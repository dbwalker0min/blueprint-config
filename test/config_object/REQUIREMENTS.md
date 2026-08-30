# BlueprintConfig Requirements

These requirements define the externally observable behavior of
`BlueprintConfig`.

`Boolean` may be used as a simple field implementation in these tests.
The behavior of `Boolean` itself is outside the scope of these requirements.

## Class definition

### BC-001 — Registration

A subclass of `BlueprintConfig` shall be registered in the
`BlueprintConfig` registry.

### BC-002 — Configuration with no fields

A subclass containing no fields shall produce an error build diagnostic.

### BC-003 — Valid configuration

A subclass containing valid fields shall produce no build diagnostics.

## Blueprint generation

### BC-010 — Field inclusion

Each field declared on the configuration class shall appear in the
generated blueprint fragment using its attribute name as the input key.

...

## Loading

### BC-020 — Supplied value

A supplied field value shall be available from the corresponding
configuration instance attribute.

### BC-021 — Default value

If no value is supplied and the field has a default, the default shall
be used.

...