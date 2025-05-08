import logging
from typing import Optional, List

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.models import Category
from agents.protocol.schemas import CategoryCreate, CategoryUpdate, CategoryDTO, CategoryType

logger = logging.getLogger(__name__)

async def create_category(
    category: CategoryCreate,
    user: dict,
    session: AsyncSession
) -> CategoryDTO:
    """Create a new category"""
    try:
        new_category = Category(
            name=category.name,
            type=category.type,
            description=category.description,
            tenant_id=user.get('tenant_id')
        )
        session.add(new_category)
        await session.commit()
        await session.refresh(new_category)
        return CategoryDTO.model_validate(new_category)
    except Exception as e:
        logger.error(f"Error creating category: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.API_CALL_ERROR,
            f"Failed to create category: {str(e)}"
        )

async def update_category(
    category_id: int,
    category: CategoryUpdate,
    user: dict,
    session: AsyncSession
) -> CategoryDTO:
    """Update an existing category"""
    try:
        # Verify category exists and belongs to user
        result = await session.execute(
            select(Category).where(
                Category.id == category_id,
                Category.tenant_id == user.get('tenant_id')
            )
        )
        db_category = result.scalar_one_or_none()
        if not db_category:
            raise CustomAgentException(
                ErrorCode.RESOURCE_NOT_FOUND,
                "Category not found or no permission"
            )

        # Update fields
        update_data = category.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_category, key, value)

        await session.commit()
        await session.refresh(db_category)
        return CategoryDTO.model_validate(db_category)
    except CustomAgentException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.API_CALL_ERROR,
            f"Failed to update category: {str(e)}"
        )

async def delete_category(
    category_id: int,
    user: dict,
    session: AsyncSession
):
    """Delete a category"""
    try:
        result = await session.execute(
            select(Category).where(
                Category.id == category_id,
                Category.tenant_id == user.get('tenant_id')
            )
        )
        category = result.scalar_one_or_none()
        if not category:
            raise CustomAgentException(
                ErrorCode.RESOURCE_NOT_FOUND,
                "Category not found or no permission"
            )

        await session.delete(category)
        await session.commit()
    except CustomAgentException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.API_CALL_ERROR,
            f"Failed to delete category: {str(e)}"
        )

async def get_categories(
    type: Optional[CategoryType],
    user: Optional[dict],
    session: AsyncSession
) -> List[CategoryDTO]:
    """Get all categories by type"""
    try:
        conditions = []
        if user and user.get('tenant_id'):
            conditions.append(
                or_(
                    Category.tenant_id == user.get('tenant_id'),
                    Category.tenant_id.is_(None)
                )
            )
        else:
            # For non-logged-in users, only show public categories (tenant_id is None)
            conditions.append(Category.tenant_id.is_(None))
            
        if type:
            conditions.append(Category.type == type)

        result = await session.execute(
            select(Category)
            .where(and_(*conditions))
            .order_by(Category.sort_order.asc(), Category.create_time.asc())
        )
        categories = result.scalars().all()
        
        # Convert SQLAlchemy objects to dictionaries
        return [CategoryDTO.model_validate({
            'id': cat.id,
            'name': cat.name,
            'type': cat.type,
            'description': cat.description,
            'tenant_id': cat.tenant_id,
            'sort_order': cat.sort_order,
            'create_time': cat.create_time.isoformat() if cat.create_time else None,
            'update_time': cat.update_time.isoformat() if cat.update_time else None
        }) for cat in categories]
    except Exception as e:
        logger.error(f"Error getting categories: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.API_CALL_ERROR,
            f"Failed to get categories: {str(e)}"
        )

async def get_category(
    category_id: int,
    user: Optional[dict],
    session: AsyncSession
) -> CategoryDTO:
    """Get a specific category"""
    try:
        conditions = [Category.id == category_id]
        if user and user.get('tenant_id'):
            conditions.append(
                or_(
                    Category.tenant_id == user.get('tenant_id'),
                    Category.tenant_id.is_(None)
                )
            )
        else:
            # For non-logged-in users, only show public categories
            conditions.append(Category.tenant_id.is_(None))
            
        result = await session.execute(
            select(Category).where(and_(*conditions))
        )
        category = result.scalar_one_or_none()
        if not category:
            raise CustomAgentException(
                ErrorCode.RESOURCE_NOT_FOUND,
                "Category not found or no permission"
            )
        return CategoryDTO.model_validate(category)
    except CustomAgentException:
        raise
    except Exception as e:
        logger.error(f"Error getting category: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.API_CALL_ERROR,
            f"Failed to get category: {str(e)}"
        ) 