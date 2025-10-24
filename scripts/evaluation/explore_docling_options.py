#!/usr/bin/env python3
"""Explore all available Docling configuration options."""

from docling.datamodel.pipeline_options import PdfPipelineOptions

# Create default pipeline options
opts = PdfPipelineOptions()

print("=" * 80)
print("PdfPipelineOptions - Available Configuration Parameters")
print("=" * 80)
print()

# Get all fields from the model
for field, value in opts.model_dump().items():
    value_type = type(value).__name__
    print(f"{field}:")
    print(f"  Type: {value_type}")
    print(f"  Default: {value}")
    print()

# Also check model fields for more info
print("=" * 80)
print("Field Descriptions (from model schema)")
print("=" * 80)
print()

schema = opts.model_json_schema()
properties = schema.get("properties", {})

for field_name, field_info in properties.items():
    print(f"{field_name}:")
    if "description" in field_info:
        print(f"  Description: {field_info['description']}")
    if "type" in field_info:
        print(f"  Type: {field_info['type']}")
    if "default" in field_info:
        print(f"  Default: {field_info['default']}")
    print()
