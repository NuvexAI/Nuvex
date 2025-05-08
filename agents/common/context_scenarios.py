# Supported scenarios for agent context storage
# This list can be extended in the future
SUPPORTED_CONTEXT_SCENARIOS = [
    "wallet_signature",  # Wallet signature data
    "public_key",
]

sensitive_config_map = {
    "wallet_signature": {
      "response": {
        "sensitive_fields": [
          {
              "path": "signedTransaction",
              "description": "Nested password field in body",
              "mask_type": "partial",
              "mask_percentage": 0.4,
              "max_mask_length": 8
          }
        ]
      }
    }
}