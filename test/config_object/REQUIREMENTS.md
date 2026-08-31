# `BlueprintConfig` Requirements

These requirements define the externally observable behavior of `BlueprintConfig`. Each numbered requirement describes one independently observable behavior of `BlueprintConfig`.

`Boolean` and `Object` may be used as a simple field implementation in these tests. The behavior of these selectors themselves is outside the scope of these requirements.

------

# Use "Shall"

## Class definition

### BC-DEF-001 — Registration

A subclass of `BlueprintConfig` shall be registered in the `BlueprintConfig` registry.

### BC-DEF-002 — `BlueprintConfig` with no fields

A subclass containing no fields shall produce an error build diagnostic.

### BC-DEF-003 — Valid configuration

A subclass containing valid fields shall produce no build diagnostics.

## Blueprint generation

### BC-GEN-001 — Blueprint Fields inclusion

Each field declared on the `BlueprintConfig` class shall appear in the generated blueprint fragment using its attribute name as the input key. The fields should be generated so they are consistent with `input` blueprint sections, i.e. support the parameters `name`, `description`, `default`, and `selector`.

### BC-GEN-002 — Blueprint name shall be specified by class variable

### BC-GEN-002 — Blueprint author shall be specified by class variable

### BC-GEN-002 — Blueprint description shall be specified by class variable

### BC-GEN-002 — Blueprint minimum version shall be specified by class variable

### BC-GEN-002 — Blueprint name shall be specified by class variable



### BC-GEN-013 — Blueprint file location

The blueprint shall be written to the location specified by the `Path` class variable named `blueprint_path`.

## Loading

### BC-LOAD-001 — Supplied value

A supplied field value shall be available from the corresponding configuration instance attribute.

### BC-LOAD-002 — Default value

If no value is supplied and the field has a default, use the default.

### BC-LOAD-003 — No value specified, `None` allowed, and no default

If the

### BC-LOAD-004 — No value specified, `None` not allowed, and no default

If no value is supplied for a field, the field has no default value, and the field does not allow `None`, an error load diagnostic shall be generated.

## Generation

### BC-GEN-001 — A blueprint should be written at the file pointed to by the class variable

## Input sections

For `min_version` ≥ 2026.6.0, input sections will be supported

### BC-INPSEC-001 — Support of input sections

