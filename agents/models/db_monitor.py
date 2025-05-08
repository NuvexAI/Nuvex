import asyncio
import logging
import random

import aiomysql

from agents.common.config import SETTINGS

logger = logging.getLogger(__name__)

class DatabaseMonitor:
    def __init__(self, check_interval=300):  # Default check every 5 minutes
        self.check_interval = check_interval
        self.running = False
        self.task = None
        
    async def connect(self):
        """Create admin connection for monitoring"""
        try:
            conn = await aiomysql.connect(
                host=SETTINGS.MYSQL_HOST,
                port=SETTINGS.MYSQL_PORT,
                user=SETTINGS.MYSQL_USER,
                password=SETTINGS.MYSQL_PASSWORD,
                db=SETTINGS.MYSQL_DB,
                autocommit=True,
                charset="utf8mb4",
                use_unicode=True,
                connect_timeout=10  # Connection timeout in seconds
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database for monitoring: {str(e)}")
            return None
            
    async def get_performance_schema_columns(self, conn, table_name):
        """Get the available columns in a performance_schema table"""
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SHOW COLUMNS FROM performance_schema.{table_name}")
                columns = [column[0].lower() for column in await cursor.fetchall()]
                return columns
        except Exception as e:
            logger.warning(f"Error getting columns for performance_schema.{table_name}: {e}")
            return []
    
    async def get_idle_connections(self, conn, idle_threshold=1800):
        """Get connections idle for longer than specified time"""
        # Check if performance_schema.processlist is available and get its columns
        try:
            columns = await self.get_performance_schema_columns(conn, "processlist")
            has_performance_schema = len(columns) > 0
            
            # Determine the correct column names
            id_column = "id"  # Default for information_schema
            if has_performance_schema:
                # Check which ID column exists in performance_schema
                if "processlist_id" in columns:
                    id_column = "processlist_id"
                elif "id" in columns:
                    id_column = "id"
                elif "thread_id" in columns:
                    id_column = "thread_id"
                else:
                    logger.warning("Could not find ID column in performance_schema.processlist")
                    has_performance_schema = False
        except Exception as e:
            logger.warning(f"Error checking performance_schema: {e}")
            has_performance_schema = False
            
        async with conn.cursor() as cursor:
            if has_performance_schema:
                # Use performance_schema (recommended approach)
                await cursor.execute(
                    f"SELECT {id_column}, user, host, db, command, time, state, info "
                    "FROM performance_schema.processlist "
                    "WHERE command = 'Sleep' AND time > %s AND user != 'system user'",
                    (idle_threshold,)
                )
            else:
                # Fallback to information_schema (deprecated)
                await cursor.execute(
                    "SELECT id, user, host, db, command, time, state, info "
                    "FROM information_schema.processlist "
                    "WHERE command = 'Sleep' AND time > %s AND user != 'system user'",
                    (idle_threshold,)
                )
            return await cursor.fetchall()
            
    async def kill_idle_connection(self, conn, process_id):
        """Terminate specified idle connection"""
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(f"KILL {process_id}")
                logger.info(f"Killed idle connection with ID {process_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to kill connection {process_id}: {str(e)}")
            return False
            
    async def check_and_kill_idle_connections(self):
        """Check and terminate idle connections"""
        conn = await self.connect()
        if not conn:
            return
            
        try:
            # Get connections idle for more than 30 minutes
            idle_connections = await self.get_idle_connections(conn, idle_threshold=1800)
            
            if idle_connections:
                logger.warning(f"Found {len(idle_connections)} idle connections")
                
                for process in idle_connections:
                    process_id, user, host, db, command, idle_time, state, info = process
                    logger.info(f"Idle connection: ID={process_id}, User={user}, Host={host}, "
                               f"DB={db}, Time={idle_time}s, State={state}")
                    
                    # Terminate idle connection
                    await self.kill_idle_connection(conn, process_id)
            else:
                logger.debug("No idle connections found")
                
        except Exception as e:
            logger.error(f"Error checking idle connections: {str(e)}")
        finally:
            conn.close()
            
    async def check_blocking_operations(self):
        """Check for blocking operations"""
        conn = await self.connect()
        if not conn:
            return
            
        try:
            # Check if performance_schema.processlist is available and get its columns
            try:
                columns = await self.get_performance_schema_columns(conn, "processlist")
                has_performance_schema = len(columns) > 0
                
                # Determine the correct column names
                id_column = "id"  # Default for information_schema
                if has_performance_schema:
                    # Check which ID column exists in performance_schema
                    if "processlist_id" in columns:
                        id_column = "processlist_id"
                    elif "id" in columns:
                        id_column = "id"
                    elif "thread_id" in columns:
                        id_column = "thread_id"
                    else:
                        logger.warning("Could not find ID column in performance_schema.processlist")
                        has_performance_schema = False
            except Exception as e:
                logger.warning(f"Error checking performance_schema: {e}")
                has_performance_schema = False
                
            async with conn.cursor() as cursor:
                # First check if the sys schema is available
                try:
                    await cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'sys' AND table_name = 'schema_table_lock_waits'")
                    sys_schema_available = await cursor.fetchone() is not None
                except Exception:
                    sys_schema_available = False
                
                if sys_schema_available:
                    try:
                        # Check for metadata lock waits - first check available columns
                        await cursor.execute("SHOW COLUMNS FROM sys.schema_table_lock_waits")
                        columns = [column[0].lower() for column in await cursor.fetchall()]
                        
                        # Build query dynamically based on available columns
                        select_columns = ["waiting_pid"]
                        if "waiting_query" in columns:
                            select_columns.append("waiting_query")
                        if "blocking_pid" in columns:
                            select_columns.append("blocking_pid")
                        if "blocking_query" in columns:
                            select_columns.append("blocking_query")
                            
                        # Check for wait time column - different MySQL versions use different names
                        wait_time_column = None
                        for possible_name in ["wait_age", "wait_age_secs", "wait_time"]:
                            if possible_name in columns:
                                wait_time_column = possible_name
                                select_columns.append(possible_name)
                                break
                                
                        if select_columns:
                            query = f"SELECT {', '.join(select_columns)} FROM sys.schema_table_lock_waits"
                            await cursor.execute(query)
                            locks = await cursor.fetchall()
                            
                            if locks:
                                logger.warning(f"Found {len(locks)} metadata lock waits")
                                for lock in locks:
                                    log_parts = []
                                    
                                    # Extract values safely
                                    idx = 0
                                    waiting_pid = lock[idx] if idx < len(lock) else "Unknown"
                                    log_parts.append(f"Waiting PID={waiting_pid}")
                                    
                                    if "blocking_pid" in columns:
                                        idx = select_columns.index("blocking_pid")
                                        blocking_pid = lock[idx] if idx < len(lock) else "Unknown"
                                        log_parts.append(f"Blocking PID={blocking_pid}")
                                    
                                    if wait_time_column:
                                        idx = select_columns.index(wait_time_column)
                                        wait_time = lock[idx] if idx < len(lock) else "Unknown"
                                        log_parts.append(f"Wait time={wait_time}s")
                                    
                                    logger.warning(f"Lock wait: {', '.join(log_parts)}")
                    except Exception as e:
                        logger.warning(f"Error querying sys.schema_table_lock_waits: {str(e)}")
                        # Fall back to information_schema
                        sys_schema_available = False
                
                # Alternative approach using information_schema if sys schema is not available or had errors
                if not sys_schema_available:
                    try:
                        logger.info("Using information_schema for lock detection")
                        # Check if innodb_lock_waits table exists
                        await cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'information_schema' AND table_name = 'innodb_lock_waits'")
                        if await cursor.fetchone():
                            await cursor.execute(
                                "SELECT r.trx_id, r.trx_mysql_thread_id waiting_thread, "
                                "b.trx_id, b.trx_mysql_thread_id blocking_thread, "
                                "TIMESTAMPDIFF(SECOND, r.trx_wait_started, NOW()) wait_time "
                                "FROM information_schema.innodb_lock_waits w "
                                "JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id "
                                "JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id"
                            )
                            locks = await cursor.fetchall()
                            
                            if locks:
                                logger.warning(f"Found {len(locks)} lock waits")
                                for lock in locks:
                                    if len(lock) >= 5:
                                        _, waiting_pid, _, blocking_pid, wait_time = lock
                                        logger.warning(
                                            f"Lock wait: Waiting PID={waiting_pid}, Blocking PID={blocking_pid}, "
                                            f"Wait time={wait_time}s"
                                        )
                        else:
                            # Simplified approach if innodb_lock_waits is not available
                            logger.info("Using processlist for basic lock detection")
                            await self.check_waiting_processes(conn, cursor, has_performance_schema, id_column)
                    except Exception as e:
                        logger.warning(f"Error using alternative lock detection: {str(e)}")
                
                # Check for long-running queries
                try:
                    if has_performance_schema:
                        # Use performance_schema (recommended)
                        await cursor.execute(
                            f"SELECT {id_column}, user, host, db, command, time, state, info "
                            "FROM performance_schema.processlist "
                            "WHERE command != 'Sleep' AND time > 60 "  # Queries running for more than 60 seconds
                            "AND user != 'event_scheduler' "  # Exclude event scheduler
                            "AND user != 'system user' "  # Exclude system user
                            "AND command NOT IN ('Daemon', 'Binlog Dump', 'Binlog Dump GTID') "  # Exclude system processes
                        )
                    else:
                        # Fallback to information_schema (deprecated)
                        await cursor.execute(
                            "SELECT id, user, host, db, command, time, state, info "
                            "FROM information_schema.processlist "
                            "WHERE command != 'Sleep' AND time > 60 "  # Queries running for more than 60 seconds
                            "AND user != 'event_scheduler' "  # Exclude event scheduler
                            "AND user != 'system user' "  # Exclude system user
                            "AND command NOT IN ('Daemon', 'Binlog Dump', 'Binlog Dump GTID') "  # Exclude system processes
                        )
                    long_queries = await cursor.fetchall()
                    
                    if long_queries:
                        logger.warning(f"Found {len(long_queries)} long-running queries")
                        for query in long_queries:
                            if len(query) >= 7:  # Ensure we have enough elements
                                # Process ID is at different positions depending on the schema used
                                process_id = query[0]  # Both schemas have process ID at position 0
                                user, host, db, command, run_time, state = query[1:7]
                                info = query[7] if len(query) > 7 else None
                                logger.warning(
                                    f"Long query: ID={process_id}, User={user}, DB={db or 'None'}, "
                                    f"Time={run_time}s, State={state}, Query={info[:100] if info else 'None'}..."
                                )
                    
                    # Separately log system processes if they've been running for an extremely long time
                    if has_performance_schema:
                        # Use performance_schema
                        await cursor.execute(
                            f"SELECT {id_column}, user, host, db, command, time, state, info "
                            "FROM performance_schema.processlist "
                            "WHERE (user = 'event_scheduler' OR user = 'system user' OR "
                            "command IN ('Daemon', 'Binlog Dump', 'Binlog Dump GTID')) "
                            "AND time > 86400"  # Running for more than 1 day
                        )
                    else:
                        # Fallback to information_schema
                        await cursor.execute(
                            "SELECT id, user, host, db, command, time, state, info "
                            "FROM information_schema.processlist "
                            "WHERE (user = 'event_scheduler' OR user = 'system user' OR "
                            "command IN ('Daemon', 'Binlog Dump', 'Binlog Dump GTID')) "
                            "AND time > 86400"  # Running for more than 1 day
                        )
                    system_processes = await cursor.fetchall()
                    
                    if system_processes and logger.isEnabledFor(logging.DEBUG):  # Only log at debug level
                        logger.debug(f"Found {len(system_processes)} long-running system processes")
                        for process in system_processes:
                            if len(process) >= 7:
                                process_id = process[0]
                                user, host, db, command, run_time, state = process[1:7]
                                logger.debug(
                                    f"System process: ID={process_id}, User={user}, Command={command}, "
                                    f"Time={run_time}s, State={state}"
                                )
                except Exception as e:
                    logger.warning(f"Error checking long-running queries: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Error checking blocking operations: {str(e)}")
        finally:
            conn.close()
            
    async def monitor_loop(self):
        """Monitoring loop"""
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while self.running:
            try:
                # Add some randomness to the check interval to avoid all servers checking at the same time
                jitter = self.check_interval * 0.1  # 10% jitter
                actual_interval = self.check_interval + (random.random() * 2 - 1) * jitter
                
                logger.info("Running database connection monitor check")
                
                # Check and kill idle connections
                try:
                    await self.check_and_kill_idle_connections()
                    consecutive_errors = 0  # Reset error counter on success
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"Error in check_and_kill_idle_connections: {str(e)}", exc_info=True)
                
                # Check for blocking operations
                try:
                    await self.check_blocking_operations()
                    consecutive_errors = 0  # Reset error counter on success
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"Error in check_blocking_operations: {str(e)}", exc_info=True)
                
                # If we've had too many consecutive errors, increase the check interval temporarily
                if consecutive_errors >= max_consecutive_errors:
                    logger.warning(f"Had {consecutive_errors} consecutive errors, increasing check interval temporarily")
                    actual_interval = min(self.check_interval * 2, 1800)  # Max 30 minutes
                
                logger.debug(f"Next database monitor check in {actual_interval:.1f} seconds")
                
            except Exception as e:
                logger.error(f"Unexpected error in monitor loop: {str(e)}", exc_info=True)
                consecutive_errors += 1
            
            # Wait for the next check
            await asyncio.sleep(actual_interval)
            
    def start(self):
        """Start monitoring"""
        if self.running:
            return
            
        self.running = True
        self.task = asyncio.create_task(self.monitor_loop())
        logger.info("Database connection monitor started")
        
    async def stop(self):
        """Stop monitoring"""
        if not self.running:
            return
            
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Database connection monitor stopped")

    @staticmethod
    def set_log_level(level):
        """Set the log level for the database monitor
        
        Args:
            level: Logging level (e.g., logging.INFO, logging.DEBUG, logging.WARNING)
        """
        logger.setLevel(level)
        logger.info(f"Database monitor log level set to {logging.getLevelName(level)}")
        
        # Add a handler if none exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
    @staticmethod
    def enable_debug():
        """Enable debug logging for the database monitor"""
        DatabaseMonitor.set_log_level(logging.DEBUG)
        
    @staticmethod
    def enable_info():
        """Enable info logging for the database monitor"""
        DatabaseMonitor.set_log_level(logging.INFO)
        
    @staticmethod
    def enable_warning_only():
        """Enable warning-only logging for the database monitor"""
        DatabaseMonitor.set_log_level(logging.WARNING)

# Singleton instance
db_monitor = DatabaseMonitor()

# For initializing at application startup
async def start_db_monitor(log_level=logging.WARNING):
    """Start the database connection monitor
    
    Args:
        log_level: Logging level (default: logging.WARNING)
    """
    # Set log level first
    DatabaseMonitor.set_log_level(log_level)
    
    # Start the monitor
    db_monitor.start()
    logger.info("Database connection monitor started with log level: " + 
                logging.getLevelName(logger.getEffectiveLevel()))
    
# For cleanup at application shutdown
async def stop_db_monitor():
    await db_monitor.stop() 