# Abstract types

An abstract type lets generic code use an associated type while each context chooses its concrete
form. A CGP abstract-type trait declares that type, and wiring selects it for the context.

## The idea

An abstract-type trait names a type without fixing its concrete form. For example,
`trait HasNameType { type Name; }` lets generic code refer to `Self::Name` instead of choosing
`String` or another concrete type. The context supplies the type, just as it supplies the values a
provider needs through getters.

Providers can reuse the same abstract type across contexts with different concrete choices. Code
written in terms of `Self::Name` can work with `String`, `&'static str`, or a custom name type. The
abstraction remains an ordinary Rust associated type: generic functions require
`Context: HasNameType` and use `Context::Name`. CGP adds macros for declaring and wiring the trait.

## Direct implementation: it's just a trait

Implement an abstract-type trait directly to choose a concrete type for a context. In this example,
the ordinary Rust impl sets `Person::Name` to `String`:

```rust
#[cgp_type]
pub trait HasNameType {
    type Name;
}

pub struct Person;

impl HasNameType for Person {
    type Name = String;
}
```

The direct impl fixes `Person::Name` to `String` for generic code using `HasNameType`. Use this form
to explain abstract types to newcomers: the context implements a trait and specifies its associated
type. The wiring form below makes the same choice through a delegation table.

## Making a type swappable with `#[cgp_type]`

`#[cgp_type]` generates a component whose associated type can be selected through wiring. Apply it
to a trait with exactly one associated type and without methods. It generates the consumer trait,
provider trait, blanket impls, and component marker that `#[cgp_component]` would generate, with
impls forwarding the associated type:

```rust
#[cgp_type]
pub trait HasNameType {
    type Name;
}
```

The associated type determines the default provider name. `type Name;` produces `NameTypeProvider`
and `NameTypeProviderComponent`. Override the provider name with an argument such as
`#[cgp_type(ProvideName)]`.

Bounds on the associated type apply throughout the expansion. For example, `type Name: Clone;`
requires the concrete type selected by the context to implement `Clone`.

`#[cgp_type]` differs from a plain component in one extra blanket impl, for the `UseType` provider
described next. That impl lets a context pick a concrete type without writing a provider of its own.

## Wiring a concrete type with `UseType`

Wire an abstract-type component to `UseType<T>` to select `T` as its concrete type. `#[cgp_type]`
generates a blanket provider impl for `UseType<Name>` that sets the associated type to `Name`, so
the context can name its choice directly in the table:

```rust
delegate_components! {
    Person {
        NameTypeProviderComponent: UseType<String>,
    }
}
```

This entry makes `Person` implement `HasNameType` with `Name = String` without a custom provider.
The selected type must satisfy any associated-type bounds. `UseType<T>` is a zero-sized marker named
in the table and never constructed. It supplies a type much as `UseField` supplies a getter value;
see [functions and getters](functions-and-getters.md).

`#[cgp_type]` generates this blanket impl to supply the associated type from the provider parameter:

```rust
impl<Name, __Context__> NameTypeProvider<__Context__> for UseType<Name> {
    type Name = Name;
}
```

This says `UseType<T>` is a provider that supplies `T` as the abstract type, for any context. If the
associated type carried a bound, that bound would be copied into the impl's `where` clause, so the
concrete type must satisfy it.

`UseType<T>` and `#[use_type]` serve different purposes. The provider struct `UseType<T>` selects a
concrete type through wiring. The attribute `#[use_type]` imports an abstract type into a definition
and rewrites bare uses of its name.

## The built-in `HasType` / `TypeProvider` component

`HasType<Tag>` is CGP's built-in abstract-type component. Its provider trait is `TypeProvider`, and
each tag identifies a separate type choice. A context can therefore select several abstract types
through wiring:

```rust
#[cgp_component(TypeProvider)]
pub trait HasType<Tag> {
    type Type;
}
```

`#[cgp_type]` adapts the built-in `HasType` component to a named abstract type. It generates an
internal `WithProvider` impl that adapts `TypeProvider`, allowing `UseType<T>` to supply both
built-in and user-defined abstract types.

Prefer a descriptive trait such as `HasNameType` for routine use. It exposes `Self::Name` and its
own provider while using `HasType` underneath. To name the adapter explicitly, use `WithType<T>`, an
alias in the [WithProvider family](wiring.md).

## Choosing the concrete type from a table with `UseDelegatedType`

Use `UseDelegatedType<Components>` when a group of related types must be selected together. It looks
up each concrete type in an inner `DelegateComponent` table keyed by the type tag. One provider can
then supply several abstract-type components or use choices recorded elsewhere. For a single
concrete type per component, prefer `UseType<T>`.

`UseDelegatedType` reads the same kind of table as `UseDelegate`, but returns a type. Its
`WithProvider` alias is `WithDelegatedType`. See [wiring](wiring.md) for the corresponding per-value
dispatch of behavior.

## Abstract type as a getter return type

Declare an associated type directly in `#[cgp_auto_getter]` when only that getter needs it. The
field determines the concrete type, so a separate `#[cgp_type]` trait is unnecessary:

```rust
#[cgp_auto_getter]
pub trait HasName {
    type Name;

    fn name(&self) -> &Self::Name;
}
```

The context supplies both the concrete `Name` and the value through its field. This keeps the type
local to the getter that uses it. See [functions and getters](functions-and-getters.md) for the
generated field access.

## Importing an abstract type with `#[use_type]`

Prefer `#[use_type]` when a definition needs an abstract type from another trait. It lets the
definition use a bare name such as `Scalar` or `Error` while the macro generates a qualified path
such as `<Self as HasScalarType>::Scalar`.

Declare imports alongside `#[cgp_fn]`, `#[cgp_impl]`, or `#[cgp_component]` with
`#[use_type(Trait.AssocType)]`. The dot separates the trait from its associated type, including when
the trait has a path or generic arguments, as in `errors::HasErrorType.Error` or
`HasFooType<X>.Foo`.

The attribute rewrites the imported name and adds the required trait bound. For `#[cgp_component]`,
it adds a supertrait; for `#[cgp_impl]` and `#[cgp_fn]`, it adds a `where` bound. Here,
`rectangle_area` uses the imported `Scalar` for its fields and return type:

```rust
pub trait HasScalarType {
    type Scalar: Clone + Mul<Output = Self::Scalar>;
}

#[cgp_fn]
#[use_type(HasScalarType.Scalar)]
fn rectangle_area(
    &self,
    #[implicit] width: Scalar,
    #[implicit] height: Scalar,
) -> Scalar {
    width * height
}
```

The expansion qualifies each `Scalar` and adds the trait requirements. The resulting trait and impl
are:

```rust
pub trait RectangleArea: HasScalarType {
    fn rectangle_area(&self) -> <Self as HasScalarType>::Scalar;
}

impl<Context> RectangleArea for Context
where
    Self: HasField<Symbol!("width"), Value = <Self as HasScalarType>::Scalar>
        + HasField<Symbol!("height"), Value = <Self as HasScalarType>::Scalar>,
    Self: HasScalarType,
{
    fn rectangle_area(&self) -> <Self as HasScalarType>::Scalar {
        let width: <Self as HasScalarType>::Scalar =
            self.get_field(PhantomData::<Symbol!("width")>).clone();
        let height: <Self as HasScalarType>::Scalar =
            self.get_field(PhantomData::<Symbol!("height")>).clone();
        width * height
    }
}
```

The substitution matches single-segment type paths without arguments whose identifier equals the
imported name. It rewrites matching return types, implicit-argument annotations, and `let` bindings
alike. The qualified result identifies which trait supplies the type and avoids ambiguity.

Additional import forms support named contexts, dependent types, aliases, and equality constraints.

Use `in Context` to import an associated type from a named type instead of `Self`. For example,
`#[use_type(HasScalarType.Scalar in Types)]` rewrites `Scalar` to `<Types as HasScalarType>::Scalar`
and adds `Types: HasScalarType` as a `where` bound. The bound appears on the generated impl and, for
`#[cgp_fn]` and `#[cgp_component]`, on the generated trait. A plain `<Types>` parameter is
sufficient; do not repeat the bound manually.

Imports can refer to other imports in the same attribute. A context can be an imported type:
`HasTypes.Types, HasScalarType.Scalar in Types` resolves `Scalar` to
`<<Self as HasTypes>::Types as HasScalarType>::Scalar`. A trait argument can also be imported:
`HasDbType.Db, HasPoolType<Db>.Pool` projects against `HasPoolType<<Self as HasDbType>::Db>`. Import
order does not matter, and several imports may use the same context.

Import dependencies must not form a cycle. For example, `HasA.A in B, HasB.B in A` and
`HasAType.A in A` are rejected. The compiler reports the cycle directly.

Use a braced list to import several types from one trait, rename them with `as`, or constrain them
with `=`. For example, `#[use_type(HasScalarType.{Scalar = f64})]` imports `Scalar` and adds
`Self: HasScalarType<Scalar = f64>`. Existing trait arguments are retained:
`HasFooType<u8>.{Foo = u32}` produces `Self: HasFooType<u8, Foo = u32>`. Prefer this equality form
over an explicit associated-type equality bound on `#[cgp_impl]` or `#[cgp_fn]`.

Equality constraints also substitute imported aliases on the right-hand side.
`#[use_type(HasPasswordType.Password, HasHashedPasswordType.{HashedPassword = Password})]` equates
the types by adding
`Self: HasHashedPasswordType<HashedPassword = <Self as HasPasswordType>::Password>`. Substitution
also applies inside a larger type:
`#[use_type(HasDbType.Db, HasTransactionType.{Transaction = Tx<Db>})]` adds
`Self: HasTransactionType<Transaction = Tx<<Self as HasDbType>::Db>>`.

Use equality constraints only on `#[cgp_fn]` and `#[cgp_impl]`. `#[cgp_component]` rejects the
`= ...` form because it produces an impl-side equality constraint.

Combine imports from several traits in one comma-separated attribute, as in
`#[use_type(HasUserIdType.UserId, HasCurrencyType.Currency, HasErrorType.Error)]`. Stacked
attributes behave identically, but prefer one import list unless there is a reason to separate it.

Every imported identifier or alias must be unique across the attribute specifications and within
each braced list. Duplicate names make substitution ambiguous and produce a compile error on every
host macro.

## Sharing one type across contexts

A context can select one abstract type for all providers and traits that depend on it. Every use of
its `Self::Scalar` refers to the same choice. For example, a context implementing
`CanCalculateAreaOfShape<Shape>` for several shapes can supply `Scalar` through `HasScalarType`. The
shapes need not define scalar types themselves. Changing the context's wiring from `UseType<f32>` to
`UseType<f64>` changes the scalar for all those shapes.

The same pattern shares an error type across an application. `HasErrorType` is defined with
`#[cgp_type]`, and fallible providers use the context's common `Self::Error`; see [error
handling](error-handling.md).

## Related references

These references explain how abstract types connect to other CGP constructs:

- [Components](components.md): The traits and providers used to wire an abstract type.
- [Functions and getters](functions-and-getters.md): Code that uses abstract types and reads values.
- [Higher-order providers](higher-order-providers.md): Provider composition and generic parameters.
- [Error handling](error-handling.md): Sharing one error type across a context.

## Further reference

Consult the online knowledge base for complete syntax and expansions:

- [`#[cgp_type]`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_type.md)
- [`HasType`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/components/has_type.md)
- [`UseType` provider](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/providers/use_type.md)
- [`#[use_type]` attribute](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/attributes/use_type.md)
