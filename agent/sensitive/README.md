# Sensitive Data Processor

This module provides functionality to handle sensitive data in tool responses and parameters. It allows masking sensitive data in API responses and recovering original data when needed for subsequent API calls.

## Features

- Mask sensitive data in API responses based on configuration
- Support for different masking types (full, partial, pattern) with human-friendly output
- Automatic recovery of sensitive data when used as parameters in subsequent API calls
- Support for both flat key-value parameters and nested JSON structures
- Redis-based storage for sensitive data mappings, supporting multi-instance deployments
- Conversation-specific data handling with automatic cleanup
- Reverse lookup for masked values to improve recovery accuracy
- Parameter flagging to explicitly mark sensitive data
- Custom identifiers for precise binding between masked and original values
- Configurable Redis expiration time (default: 7 days)

## Configuration

Sensitive data handling is configured at the tool level by adding a `sensitive_data_config` field to the `ToolInfo` object. This configuration specifies which fields in the response should be masked and which parameters should be recovered.

### Configuration Structure

```json
{
  "response": {
    "sensitive_fields": [
      {
        "path": "data.user.password",
        "mask_type": "full",
        "max_mask_length": 8,
        "description": "User password - completely masked"
      },
      {
        "path": "data.user.email",
        "mask_type": "pattern",
        "pattern": "{username}@***",
        "description": "User email - username preserved, domain masked"
      },
      {
        "path": "data.auth.token",
        "mask_type": "full",
        "max_mask_length": 8,
        "add_flag": true,
        "description": "Authentication token - completely masked and flagged as sensitive"
      },
      {
        "path": "data.user.api_key",
        "mask_type": "full",
        "identifier": "user_api_key",
        "description": "User API key with custom identifier for precise recovery"
      }
    ]
  },
  "parameters": {
    "recoverable_fields": [
      "password",
      "credit_card",
      "api_key"
    ],
    "nested_fields": [
      {
        "path": "auth.credentials.password",
        "description": "Nested password field in body"
      }
    ],
    "description": "Fields that should be recovered when used as parameters"
  }
}
```

### Path Specification

The `path` field uses dot notation to specify the location of sensitive data in the response JSON:

- Simple paths: `data.user.password`
- Array indices: `data.transactions[0].amount`
- Array wildcards: `data.api_keys[*].key` (applies to all elements in the array)

### Mask Types

- `full`: Completely masks the value (e.g., `********`)
  - `max_mask_length`: Maximum length of the mask characters (default: 8)
- `partial`: Partially masks the value, preserving some characters at the beginning and end
  - `mask_percentage`: Percentage of the string to mask (0.0 to 1.0)
  - `max_mask_length`: Maximum length of the mask characters (default: 10)
- `pattern`: Uses a specific pattern for masking
  - `pattern`: The pattern to use, with placeholders:
    - `{value}`: The original value
    - `{username}`: For email addresses, the username part
    - `{last4}`: The last 4 characters of the value

### Additional Configuration Options

- `add_flag`: When set to `true`, the masked value will be wrapped in a dictionary with a flag indicating it's sensitive data. This ensures the value will be recovered even if the field name is not in the `recoverable_fields` list.
  ```json
  {
    "__sensitive": true,
    "value": "********"
  }
  ```

- `identifier`: A custom string identifier that creates a precise binding between the masked and original values. This ensures exact recovery even when multiple fields have similar masked values.
  ```json
  {
    "path": "data.user.api_key",
    "mask_type": "full",
    "identifier": "user_api_key"
  }
  ```
  
  When combined with `add_flag`, the binding key is included in the output:
  ```json
  {
    "__sensitive": true,
    "value": "********",
    "__binding_key": "user_api_key"
  }
  ```

### Masking Examples

#### Full Masking

Full masking completely hides the original value, replacing it with asterisks.

**Configuration:**
```json
{
  "path": "data.api_key",
  "mask_type": "full",
  "max_mask_length": 8
}
```

**Original Value:**
```
sk_live_51NzQRtKL......e5TMX8dT7w8kKLzDQM
```

**Masked Value:**
```
********
```

#### Partial Masking

Partial masking preserves some characters at the beginning and end of the value, masking the middle portion.

**Configuration:**
```json
{
  "path": "data.user.address",
  "mask_type": "partial",
  "mask_percentage": 0.7,
  "max_mask_length": 6
}
```

**Original Value:**
```
123 Main Street, Apartment 456, New York, NY 10001
```

**Masked Value:**
```
123 ****** 10001
```

#### Pattern Masking

Pattern masking uses a specific pattern with placeholders for parts of the original value.

**Example 1: Email Address**

**Configuration:**
```json
{
  "path": "data.user.email",
  "mask_type": "pattern",
  "pattern": "{username}@***"
}
```

**Original Value:**
```
john.doe@example.com
```

**Masked Value:**
```
john.doe@***
```

**Example 2: Credit Card Number**

**Configuration:**
```json
{
  "path": "data.payment.credit_card",
  "mask_type": "pattern",
  "pattern": "****-{last4}"
}
```

**Original Value:**
```
4111111111111111
```

**Masked Value:**
```
****-1111
```

#### Flagged Sensitive Data

**Configuration:**
```json
{
  "path": "data.auth.token",
  "mask_type": "full",
  "max_mask_length": 8,
  "add_flag": true
}
```

**Original Value:**
```
eyJhb.....pXVCJ9.eyJzdW.....kwIn0
```

**Masked Value:**
```json
{
  "__sensitive": true,
  "value": "********"
}
```

#### Custom Identifier

**Configuration:**
```json
{
  "path": "data.user.api_key",
  "mask_type": "full",
  "max_mask_length": 8,
  "identifier": "user_api_key"
}
```

**Original Value:**
```
sk_live_51NzQRtK......MX8dT7w8kKLzDQM
```

**Masked Value:**
```
********
```

The system will use the custom identifier "user_api_key" to create a precise binding between this masked value and the original value, ensuring exact recovery even if multiple fields have the same masked value.

#### Combined Flag and Custom Identifier

**Configuration:**
```json
{
  "path": "data.payment.secret",
  "mask_type": "full",
  "max_mask_length": 8,
  "add_flag": true,
  "identifier": "payment_secret"
}
```

**Original Value:**
```
secret_key_12345
```

**Masked Value:**
```json
{
  "__sensitive": true,
  "value": "********",
  "__binding_key": "payment_secret"
}
```

### Parameter Recovery Configuration

The parameters section supports two types of parameter recovery:

1. **Flat Key-Value Parameters**:
   - `recoverable_fields`: List of field names that should be recovered in query, header, and path parameters

2. **Nested JSON Parameters**:
   - `nested_fields`: List of path configurations for nested fields in the body parameter
   - Each nested field has a `path` that uses the same dot notation as response fields

## How Sensitive Data Recovery Works

The system uses a sophisticated mechanism to recover original sensitive values when they are used in subsequent API calls:

### 1. Unique Identifier Mechanism

When sensitive data is masked, the system:
1. Generates a unique identifier for each sensitive value (or uses a custom identifier if provided)
2. Stores a mapping between this identifier and the original value in Redis
3. The identifier includes the conversation ID and either a hash of the original value or the custom identifier

```
__SENSITIVE_DATA_{conversation_id}_{hash(value)}__
```

or with custom identifier:

```
__SENSITIVE_DATA_{conversation_id}_{custom_identifier}__
```

### 2. Recovery Methods

The system uses multiple methods to recover original values:

#### Direct Identifier Recovery
If the system can access the identifier directly (internal implementation), it simply looks up the original value in Redis.

#### Custom Identifier Recovery
If a custom identifier was provided and included in the parameter (via the `__binding_key` field), the system uses it to create the exact identifier and look up the original value.

#### Reverse Lookup
The system maintains a reverse mapping from masked values to original values. This allows direct recovery when the exact masked value is used, even without access to the identifier.

#### Pattern-Based Recovery
When the model uses masked values (like `********`) in parameters, the system:

1. Checks if the value matches known masking patterns:
   - Full mask pattern: `********`
   - Partial mask pattern: `abc***xyz`
   - Pattern mask: `****-1234`

2. For each pattern type, applies specific matching logic:
   - For full masks: Finds stored values with similar length or standard mask length
   - For partial masks: Matches values with the same prefix and suffix
   - For pattern masks: Extracts distinctive parts (like last 4 digits) and finds matching values

3. Returns the best matching original value from secure storage

#### Path-Based Recovery
For nested fields in request bodies, the system:

1. Uses the paths specified in `nested_fields` to locate potentially masked values
2. Applies the recovery methods described above
3. Replaces the masked values with their original counterparts

#### Flag-Based Recovery
For values that have been flagged as sensitive:

1. The system recognizes the `__sensitive` flag in the parameter object
2. Extracts the masked value from the `value` field
3. If a `__binding_key` is present, uses it for precise recovery
4. Otherwise, applies the other recovery methods to retrieve the original value
5. This works regardless of field name, providing an explicit way to mark sensitive data

### 3. Security Considerations

- All sensitive data mappings are stored with the conversation ID as part of the key
- Each mapping has a configurable expiration time (default: 7 days)
- The system automatically cleans up mappings when conversations end
- The recovery process is completely transparent to the model

### Parameter Recovery Examples

#### Request Body Recovery Example

This example demonstrates how sensitive data in a request body is automatically recovered when making API calls.

**Tool Configuration:**
```json
{
  "parameters": {
    "recoverable_fields": ["api_key", "token"],
    "nested_fields": [
      {
        "path": "auth.credentials.password",
        "description": "Nested password field in body"
      },
      {
        "path": "payment.card_details.number",
        "description": "Nested credit card number in body"
      }
    ]
  }
}
```

**Scenario:**
1. A previous API call returned sensitive data that was masked
2. The model uses this masked data in a subsequent API call's request body
3. The system automatically recovers the original values before making the API call

**Masked Request Body (What the Model Sees and Uses):**
```json
{
  "auth": {
    "credentials": {
      "username": "john_doe",
      "password": "********"
    }
  },
  "payment": {
    "card_details": {
      "number": "****-1111",
      "expiry": "12/25",
      "cvv": "***"
    }
  },
  "api_key": "********",
  "auth_token": {
    "__sensitive": true,
    "value": "********"
  },
  "payment_secret": {
    "__sensitive": true,
    "value": "********",
    "__binding_key": "payment_secret"
  }
}
```

**Recovered Request Body (What Actually Gets Sent to the API):**
```json
{
  "auth": {
    "credentials": {
      "username": "john_doe",
      "password": "secureP@ssw0rd!"
    }
  },
  "payment": {
    "card_details": {
      "number": "4111111111111111",
      "expiry": "12/25",
      "cvv": "***"
    }
  },
  "api_key": "xxxxx",
  "auth_token": "xxxxxxx",
  "payment_secret": "xxxxxxx"
}
```

**How It Works:**
1. The system identifies masked values in the request body using the configuration
2. For flat fields like `api_key`, it checks if they're in the `recoverable_fields` list
3. For nested fields like `auth.credentials.password` and `payment.card_details.number`, it uses the paths specified in `nested_fields`
4. For flagged fields like `auth_token`, it recognizes the `__sensitive` flag and recovers the value
5. For fields with binding keys like `payment_secret`, it uses the binding key for precise recovery
6. It retrieves the original values from the secure storage and replaces the masked values
7. The API call is made with the recovered values, ensuring proper authentication and functionality

This process is completely transparent to the model - it only sees the masked values, but the system ensures the actual API calls use the original sensitive data.

## Usage Example

### 1. Configure a Tool with Sensitive Data Handling

```python
from agents.models.entity import ToolInfo

# Create a tool with sensitive data configuration
tool = ToolInfo(
    id="user-api",
    name="get_user_info",
    type="openapi",
    origin="https://api.example.com",
    path="/users/{user_id}",
    method="GET",
    parameters={
        "path": [{"name": "user_id", "required": True}]
    },
    sensitive_data_config={
        "response": {
            "sensitive_fields": [
                {
                    "path": "data.user.password",
                    "mask_type": "full",
                    "max_mask_length": 8
                },
                {
                    "path": "data.user.email",
                    "mask_type": "pattern",
                    "pattern": "{username}@***"
                },
                {
                    "path": "data.auth.token",
                    "mask_type": "full",
                    "add_flag": true
                },
                {
                    "path": "data.user.api_key",
                    "mask_type": "full",
                    "identifier": "user_api_key"
                }
            ]
        },
        "parameters": {
            "recoverable_fields": ["password", "token"],
            "nested_fields": [
                {
                    "path": "auth.credentials.password"
                }
            ]
        }
    }
)
```

### 2. Initialize with Custom Redis Expiration

```python
# Initialize the processor with a custom Redis expiration time (14 days)
processor = SensitiveDataProcessor(conversation_id, redis_expiry_days=14)
```

### 3. Using the Tool

When the tool is used:

1. The response will have sensitive fields masked according to the configuration, with human-friendly output
2. If a subsequent API call uses masked values as parameters, they will be automatically recovered:
   - For flat key-value parameters (query, header, path), fields in `recoverable_fields` will be recovered
   - For nested JSON parameters (body), fields in `nested_fields` will be recovered
   - For flagged parameters, they will be recovered regardless of field name
   - For parameters with binding keys, precise recovery will be used

### 4. Cleanup

To clean up sensitive data mappings when a conversation ends:

```python
await chat_agent.cleanup(conversation_id)
```

## Implementation Details

- Sensitive data mappings are stored in Redis with a key pattern of `sensitive_data:{conversation_id}`
- Reverse mappings are stored with a key pattern of `sensitive_data_reverse:{conversation_id}`
- Each mapping has a configurable expiration time (default: 7 days)
- The mappings are stored as Redis hashes, with identifiers/masked values as keys and JSON-serialized original values as values
- The processor uses a unique identifier for each sensitive value, based on the conversation ID and a hash of the original value or a custom identifier
- Mask lengths are limited to reasonable values to improve readability and reduce output size

## Best Practices

1. **Be Specific**: Only mask fields that are truly sensitive to minimize performance impact
2. **Use Appropriate Mask Types**: Choose the right mask type for each field based on its sensitivity
3. **Set Reasonable Mask Lengths**: Use `max_mask_length` to keep masked output concise
4. **Use Custom Identifiers**: For critical sensitive data, use custom identifiers to ensure precise recovery
5. **Use Flags for Critical Data**: Use the `add_flag` option for critical sensitive data to ensure recovery
6. **Configure Both Parameter Types**: Use both `recoverable_fields` and `nested_fields` for complete parameter handling
7. **Set Appropriate Expiration Times**: Configure Redis expiration based on your security requirements
8. **Regular Cleanup**: Call the cleanup method when conversations end to immediately remove sensitive data
9. **Audit**: Regularly review which fields are being masked and recovered 