# Extensible data

Extensible data lets generic code read, build, deconstruct, and convert structs and enums through
named fields and variants. It represents a struct as a product of fields and an enum as a sum of
variants, with each name encoded at the type level.

Extensible-data derives expose a type’s structure to generic code. Ordinary struct literals and enum
matches name every field or variant directly. The derives instead generate a type-level description
and operations that construct, extract, and convert values through it.

Independent providers can then contribute fields or handle variants without knowing the complete
type. This supports row polymorphism and structural sum types: generic operations depend on named
parts of a type’s structure. Resolution happens at compile time. Builders, variant dispatchers, and
structural casts use the generated operations to assemble and process contexts.

Records and variants use related representations. A record contains every field at once, while an
enum contains one variant at a time. Their operations share marker, casting, and dispatch
mechanisms, with different rules for representing absent fields and excluded variants.

## The umbrella derive and its shape-specific faces

Use `#[derive(CgpData)]` to generate the full extensible-data support for a struct or enum.
`CgpRecord` and `CgpVariant` generate the same support but accept only structs and enums
respectively. Applying either to the wrong item kind is an error.

Choose a narrower derive when only part of the support is needed. `HasFields`, `HasField`,
`BuildField`, `ExtractField`, and `FromVariant` each generate a subset. The umbrella derive covers
both shapes:

```rust
#[derive(CgpData)]
pub struct Person { pub first_name: String, pub last_name: String }

#[derive(CgpData)]
pub enum Shape { Circle(Circle), Rectangle(Rectangle) }
```

Generated operations identify fields and variants by type-level tags. Named fields and variants use
`Symbol!("name")`, while tuple-struct fields use positional tags such as `Index<0>`. The same tag
identifies an entry across its generated impls.

Variant construction and extraction require exactly one unnamed payload per variant. Wrap multiple
values in a dedicated struct to give the variant one payload type. Unit, multi-field tuple, and
struct-style variants are rejected, and individual variants cannot opt out of the derive.

`#[derive(HasFields)]` accepts all variant shapes because it describes their structure without
generating variant construction or extraction. A unit variant contributes `Nil`, a newtype variant
contributes its payload, a multi-field tuple variant contributes an `Index<N>`-keyed product, and a
named-field variant contributes a `Symbol!`-keyed product inside its `Field` entry. An enum with
mixed shapes can therefore have a structural description even though the constructor and extractor
derives reject it.

Avoid enum variant names that conflict with associated types in generated impls. The restrictions
for each derive are:

| Derive | Reserved variant names |
| --- | --- |
| `HasFields` | `Fields`, `FieldsRef` |
| `FromVariant` | `Value` |
| `ExtractField` | `Value`, `Remainder`, `Extractor`, `ExtractorRef`, `ExtractorMut` |
| `CgpVariant`, `CgpData` | All names listed above |

Struct field names are unaffected because they occupy a different namespace.

Rename the conflicting variant when the compiler reports `ambiguous associated item` at a derive.
Notes for `HasFields` and `FromVariant` identify the variant. Notes for `ExtractField` point only to
the derive because its generated companion variants carry that source location, so check the
reserved names manually.

## Records: the whole-struct field view

`#[derive(HasFields)]` describes a struct through its `Fields` associated type. The type is a
[`Product!`](type-level-primitives.md) containing a `Field<Symbol!("name"), Type>` entry for each
field:

```rust
impl HasFields for Person {
    type Fields = Product![
        Field<Symbol!("first_name"), String>,
        Field<Symbol!("last_name"), String>,
    ];
}
```

The derive generates conversions between the struct and its field representation. `ToFields`
consumes a value to produce its field product, `FromFields` rebuilds the value, and `ToFieldsRef`
returns a product of references. Generic algorithms can use `HasFields`, `ToFields`, or `FromFields`
to process this structure without naming the concrete struct.

Derive `HasField` as well when code needs access to individual fields by tag. `HasField<Tag>`
supplies the per-field capability used by getters, while `HasFields` describes the complete
structure. See [functions and getters](functions-and-getters.md).

## Records: building a struct field by field

`#[derive(CgpRecord)]` and `#[derive(BuildField)]` support incremental construction checked at
compile time. They generate a partial-record struct named `__Partial{Name}` with a `MapType` marker
for each field. `IsPresent` stores a field’s value, while `IsNothing` stores `()`. The builder
starts with every field absent and can be finalized once every field is present:

```rust
let employee: Employee = Employee::builder()                    // every field IsNothing
    .build_from(person)                                         // first_name + last_name now IsPresent
    .build_field(PhantomData::<Symbol!("employee_id")>, 1)      // employee_id now IsPresent
    .finalize_build();                                          // exists only at the all-present configuration
```

`HasBuilder::builder()` creates an empty partial record, and `BuildField::build_field` changes one
field from `IsNothing` to `IsPresent`. `FinalizeBuild::finalize_build` exists only when every field
is present, so incomplete construction fails at compile time. Fields can be supplied in any order.

`IntoBuilder` converts a complete struct to an all-present partial record, and `TakeField` removes
fields individually. Both `BuildField` and `TakeField` use `UpdateField<Tag, M>`, which changes one
marker and returns the old value with the rebuilt partial record. Import `TakeField` from
`cgp::core::field::traits` to call `take_field`; it is not in the prelude.

Generated `__Partial…` companions do not inherit the original struct or enum’s attributes. A
`#[derive(Debug, Clone)]` therefore does not make a partial record or extraction remainder printable
or cloneable. Tests using `assert_eq!` on an `extract_field` result can fail for this reason. Use
`.ok()`, `.is_ok()`, or a `match` as appropriate, and read present fields through the companion’s
per-field `HasField` impls.

Use the `cgp-field-extra` optional-field extension when fields may be absent or have defaults. It
reuses `UpdateField` to fill unset fields with `Default::default()` during finalization or represent
them as `Option` through `IsOptional`. Absence can then be a runtime value. The strict builder that
requires every field remains the default.

## Records: the extensible builder pattern

`CanBuildFrom` merges a source struct’s fields into a target builder with one `build_from` call. It
walks the source’s field product, taking each field with `TakeField` and inserting it with
`BuildField`. Source and target share field names without needing to name each other.

The source must derive `HasFields` as well as `BuildField`. The recursion reads `HasFields::Fields`,
so deriving only `BuildField` produces a missing `HasFields` bound. The target needs only
`BuildField`.

The extensible builder pattern uses these operations to assemble a context from independent
providers. Each subsystem produces a small output struct, and a dispatcher merges those outputs into
the target builder before finalization. The providers need not know the final context type or one
another:

```rust
delegate_components! {
    FullAppBuilder {
        HandlerComponent:
            BuildAndMergeOutputs<App, Product![
                BuildSqliteClient,
                BuildHttpClient,
                BuildOpenAiClient,
            ]>,
    }
}
```

The dispatcher is generic over the target struct and provider list. Change one provider entry to
replace a subsystem, or use code-based dispatch to select among target structs. See
[handlers](handlers.md) for `BuildAndMergeOutputs` and related routing.

## Variants: constructing and deconstructing an enum

`#[derive(HasFields)]` represents an enum’s variants as a [`Sum!`](type-level-primitives.md) of
`Field<Symbol!("Variant"), Type>` entries using `Either` and `Void`. `#[derive(FromVariant)]`
supplies a constructor for each variant, selected by its type-level tag:

```rust
fn wrap_circle(circle: Circle) -> Shape {
    Shape::from_variant(PhantomData::<Symbol!("Circle")>, circle)   // == Shape::Circle(circle)
}
```

`#[derive(ExtractField)]` generates a partial-variant companion enum named `__Partial{Name}`. Each
variant carries a `MapType` marker. A present variant uses `IsPresent`; an excluded variant uses
`IsVoid`, which maps its payload to the uninhabited `Void` type.

`HasExtractor::to_extractor` starts with all variants marked `IsPresent`.
`ExtractField::extract_field` returns `Ok(value)` when the requested variant matches. Otherwise, it
returns `Err(remainder)` with that variant marked `IsVoid`, so later operations know it has been
ruled out:

```rust
fn area(shape: Shape) -> f64 {
    match shape.to_extractor().extract_field(PhantomData::<Symbol!("Circle")>) {
        Ok(circle) => core::f64::consts::PI * circle.radius * circle.radius,
        Err(remainder) => {
            // remainder's type now has Circle ruled out (IsVoid); try the next variant
            let rect = remainder
                .extract_field(PhantomData::<Symbol!("Rectangle")>)
                .finalize_extract_result();   // remainder is now empty; this cannot fail
            rect.width * rect.height
        }
    }
}
```

Variant extraction checks exhaustiveness at compile time. Each failed extraction rules out a
variant, and a remainder with every marker set to `IsVoid` cannot contain a value.
`FinalizeExtract::finalize_extract` handles that uninhabited remainder with an empty `match`.
`FinalizeExtractResult::finalize_extract_result` uses this guarantee to return the final `Ok` value
directly.

Adding an unhandled variant makes the final remainder inhabited and prevents compilation until the
new case is covered. This preserves the exhaustiveness guarantee of a concrete `match` without a
wildcard arm. `HasExtractorRef` and `HasExtractorMut` provide equivalent operations on borrowed
values.

## Variants: the extensible visitor pattern

The extensible visitor pattern routes each enum value to a provider for its current variant. New
variants can be added without changing existing handlers, and handlers can serve several enums that
share variants. This addresses the expression problem by separating data variants from the
operations on them.

A dispatcher derives extraction and handling steps from the enum’s `Fields`. The pipeline stops at
the matching variant and otherwise passes the remainder to the next step:

```rust
delegate_components! {
    Interpreter {
        ComputerComponent:
            UseInputDelegate<new EvalComponents {
                MathExpr: DispatchEval,         // the whole enum → variant dispatcher
                Plus<MathExpr>: EvalAdd,         // one provider per variant
                Times<MathExpr>: EvalMultiply,
                Literal<u64>: EvalLiteral,
            }>,
    }
}
```

`MathExpr` selects a context-specific provider that calls the matcher combinator. This wrapper
breaks the trait-resolution cycle between the matcher and the variant providers it calls. See
[handlers](handlers.md) for `MatchWithValueHandlers`, its borrowed form, and the handler families.

## The type-level lists underneath

Records and variants use nested type-level lists that generic providers can process one entry at a
time. A record’s `Product![A, B, C]` expands to `Cons<A, Cons<B, Cons<C, Nil>>>`. The final `Nil` is
constructible because an empty record is a valid value. Lowercase `product![..]` constructs a value
of that product type.

An enum’s `Sum![A, B]` expands to `Either<A, Either<B, Void>>`. Each step offers a choice, and the
final `Void` is uninhabited because an empty enum cannot contain a value. See [type-level
primitives](type-level-primitives.md) for both representations.

Import list operations from `cgp::core::field::traits`; they are not in the prelude. `AppendProduct`
adds a field to the end of a product, `ConcatProduct` joins products, and `MapFields` transforms
each entry. Building appends, merging concatenates, and creating a partial record maps a marker over
its fields. These type transformations are evaluated during type checking without runtime cost.

`MapFields` supports both products and sums, allowing it to generate partial records and partial
enums. Its result is named `Mapped`, while `AppendProduct` and `ConcatProduct` expose `Output`. The
library does not provide `AppendSum`.

## Structural casts between records and variants

Structural casts convert between types with compatible named fields or variants. They match entries
by name without a handwritten `From` or `TryFrom` impl. Import `CanUpcast`, `CanDowncast`,
`CanDowncastFields`, and `CanBuildFrom` from `cgp::core::field::impls`; these traits are not in the
prelude.

`CanUpcast` converts a smaller enum into one containing all its variants. It always succeeds by
extracting the source variant and rebuilding it through `FromVariant`. `CanDowncast` narrows an enum
when its current variant exists in the target, returning a remainder otherwise. Use
`CanDowncastFields` on that remainder to try another target.

`CanBuildFrom` performs the corresponding record operation by inserting source fields into a target
builder. The enum casts behave as follows:

```rust
use cgp::core::field::impls::{CanDowncast, CanUpcast};               // not in the prelude

let wide = FooBar::Foo(1).upcast(PhantomData::<FooBarBaz>);          // always succeeds
assert_eq!(wide, FooBarBaz::Foo(1));

FooBarBaz::Bar("hi".into()).downcast(PhantomData::<FooBar>).ok();    // Some(FooBar::Bar(..))
FooBarBaz::Baz(true).downcast(PhantomData::<FooBar>).ok();           // None: FooBar lacks a Baz variant
```

A provider can construct a small local enum and upcast it into a larger type. This lets it work with
only the variants it needs, much as a getter accesses one field without depending on the complete
record.

## Dispatching over extensible data

Dispatch combinators use the exposed data structure to select providers generically.
`BuildAndMergeOutputs` assembles record fields from provider outputs, while `MatchWithValueHandlers`
selects the handler for a value’s variant. These combinators derive and sequence operations from the
type’s `Fields`.

See [handlers](handlers.md) for the combinators and their handler families. The examples above
select providers through ordinary `delegate_components!` entries for each
[component](components.md).

## Further reference

These online references describe extensible data as of CGP v0.8.0:

- [Extensible records](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/extensible-records.md):
  Generic record construction and access.
- [Extensible variants](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/extensible-variants.md):
  Generic enum construction and extraction.
- [Derive references](https://github.com/contextgeneric/cgp-knowledge-base/tree/main/cgp/reference/derives):
  `derive_cgp_data.md`, `derive_cgp_record.md`, `derive_cgp_variant.md`, `derive_has_fields.md`,
  `derive_build_field.md`, `derive_extract_field.md`, and `derive_from_variant.md`.

Consult the trait references for the operations generated by those derives:

- [`HasBuilder`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/traits/has_builder.md)
- [`ExtractField`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/traits/extract_field.md)
- [`FromVariant`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/traits/from_variant.md)
- [`HasFields`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/traits/has_fields.md)
- [Structural casts](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/traits/cast.md)

The type-macro references explain the underlying list representations:

- [`Product!`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/product.md)
- [`Sum!`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/sum.md)
