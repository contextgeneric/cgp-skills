# Macro grammar and expansion rules

Use this reference to check CGP macro syntax, understand generated code, and interpret compiler
errors. It describes each macro’s custom grammar and the expansion rules that connect its input to
ordinary Rust.

Valid CGP code must satisfy both the macro parser and the Rust compiler. The grammars below describe
accepted input; the expansion rules explain the resulting traits and impls. The error guide covers
failures at either stage. Examples assume `use cgp::prelude::*;` and CGP v0.8.0.

## How to read the grammars

The grammars follow the [Rust Reference notation](https://doc.rust-lang.org/nightly/reference/notation.html).
Each line in an `ebnf` block defines a production as `Name -> Expression`. Backticks mark literal
tokens, and CamelCase names refer to other productions.

Read the operators as follows:

| Notation | Meaning |
| --- | --- |
| `x?` | Optional occurrence |
| `x*` | Zero or more occurrences |
| `x+` | One or more occurrences |
| `A` or `B`, separated by a vertical bar | Choice between alternatives |
| `( … )` | Grouping |
| Adjacent expressions | Sequence |

Undefined CamelCase names refer to existing Rust grammar productions. These include `Type`,
`Generics` for parameter lists, `GenericArgs` for argument lists, `WhereClause`, `TypePath`, and
`Expression`. Uppercase names denote lexer tokens, such as `IDENTIFIER` and `STRING_LITERAL`.

Each grammar describes only the tokens parsed by the macro. For an attribute, these are the
arguments inside `#[name(…)]` or `#[name{…}]`; for a function-like macro, they are the contents of
`name!{ … }`. The surrounding delimiters and the annotated Rust item are outside that grammar.

## Reserved identifiers the expansions introduce

Generated identifiers use double underscores to distinguish them from user-defined names.
Recognizing these names helps connect raw expansions and diagnostics to the original code. This
reference sometimes uses `Context`, `Provider`, and `Params` for readability; generated code uses
the reserved forms listed below.

The generated names identify these roles:

| Identifier | Role |
| --- | --- |
| `__Context__` | Context type parameter; can be overridden |
| `__Provider__` | Provider type parameter |
| `__context__` | Rewritten `self` receiver |
| `__Component__` | Component key parameter |
| `__Components__` | Inner delegation table |
| `__Delegate__` | Provider selected from a table |
| `__Params__` | Parameter tuple passed to `IsProviderFor` |
| `__Tag__` | Getter's field tag parameter |
| `__Table__` | Namespace table parameter |

Generated references to CGP constructs use `::cgp::macro_prelude::<Name>`. This allows expansions to
compile when the crate has `cgp` in scope without separate imports for every generated name. Do not
write these internal paths yourself.

---

## Component-definition macros

Component macros generate consumer and provider traits from a trait definition. Their arguments
select the generated names.

### `#[cgp_component]`

The argument is either a bare provider name or a comma-separated set of keyed values:

```ebnf
CgpComponentArgs -> ProviderName
                  | KeyValueArg ( `,` KeyValueArg )* `,`?

ProviderName     -> IDENTIFIER

KeyValueArg      -> `name` `:` ComponentName
                  | `provider` `:` IDENTIFIER
                  | `context` `:` IDENTIFIER

ComponentName    -> IDENTIFIER GenericArgs?
```

A bare provider name is shorthand for setting `provider` alone. In the keyed form, use braces as in
`#[cgp_component { … }]`. Keys may appear in any order, but each may appear only once and `provider`
is required.

The component name defaults to the provider name plus `Component`, as in `AreaCalculatorComponent`,
and the context name defaults to `__Context__`. The component name may carry generic arguments; the
provider name may not.

`#[cgp_component]` preserves the consumer trait and generates the provider trait, component marker,
and connecting blanket impls. In the provider trait, it moves `Self` to a leading context parameter,
rewrites the receiver accordingly, and adds `IsProviderFor<{Name}Component, Context, Params>` as a
supertrait.

The consumer blanket impl makes `Context: {Provider}<Context>` imply the consumer trait. The
provider blanket impl forwards through `DelegateComponent<{Name}Component>`, using the zero-sized
component marker as the key.

The macro also generates `UseContext` and `RedirectLookup` impls, a dispatcher impl for each
`#[derive_delegate]`, and prefix impls for `#[prefix]`. Trait generics follow the context parameter
in the provider trait and form the `IsProviderFor` `Params` tuple. See [components](components.md)
for a complete expansion.

### `#[cgp_type]` and `#[cgp_getter]`

Both reuse `CgpComponentArgs` verbatim and differ only in the default when `provider` is omitted:

```ebnf
CgpTypeArgs   -> CgpComponentArgs   // default provider: {AssocType}TypeProvider
CgpGetterArgs -> CgpComponentArgs   // default provider: strip leading `Has`, append `Getter`
```

`#[cgp_type]` derives the default provider name from the associated type: `type Scalar;` produces
`ScalarTypeProvider` and `ScalarTypeProviderComponent`. It adds a `UseType<T>` blanket impl that
supplies `T` and a `WithProvider` impl adapting the built-in `TypeProvider`. See
[abstract-types](abstract-types.md).

`#[cgp_getter]` derives its provider name by removing a leading `Has` and appending `Getter`, so
`HasName` produces `NameGetter`. It always adds a `UseFields` impl. For single-method traits, it
also adds `UseField<Tag>` and `WithProvider` impls. See
[functions-and-getters](functions-and-getters.md).

---

## Provider-writing macros

Provider macros generate implementations and matching dependency markers. Choose `#[cgp_impl]` for
consumer-style method signatures or the lower-level macros for explicit provider-trait impls.

### `#[cgp_impl]`

The argument names the provider, optionally preceded by `new` and followed by a component override:

```ebnf
CgpImplArgs   -> `new`? ProviderType ( `:` ComponentType )?

ProviderType  -> Type
ComponentType -> Type
```

`ProviderType` becomes the implementing type in the generated provider impl. It can be a name, a
generic type such as `ScaledArea<Inner>`, or the literal `Self`. Adding `new` also declares the
public provider struct.

The optional `: ComponentType` overrides the component used in `IsProviderFor`. Without it, the
component name is the provider trait’s name plus `Component`.

Prefer an impl header that omits `for Context`; the macro inserts `__Context__`. Use
`impl<Context> Trait for Context` only when the context must be named or bounded explicitly, such as
for a lifetime or higher-ranked trait bound the shorthand cannot express.

`#[cgp_impl(Self)]` emits a direct consumer-trait impl while still applying companion attributes
such as `#[use_provider]`. This form requires `for Context` and ignores `new` and the component
override.

`#[cgp_impl]` expands through `#[cgp_provider]`, or `#[cgp_new_provider]` when `new` is present. It
places the context in the provider trait’s leading parameter and the provider type in the impl’s
`Self` position. It rewrites `&self` to `__context__: &__Context__`, uses of `self` to the context
value, and uses of `Self` to the context type.

Body rewriting respects nested items’ own `self` and `Self` meanings. Macro invocations are an
exception: the token rewrite cannot identify their scopes, so it rewrites those names inside
`macro!(…)` tokens too. See [components](components.md).

### `#[cgp_provider]` and `#[cgp_new_provider]`

Both take a single optional component type. `#[cgp_new_provider]` additionally declares the provider struct, implied by the name rather than the argument:

```ebnf
CgpProviderArgs    -> ComponentType?
CgpNewProviderArgs -> ComponentType?

ComponentType      -> Type
```

These macros preserve the provider-trait impl and generate `IsProviderFor` with the same `where`
bounds. The marker impl omits method bodies and associated types. Its arguments are the selected
component, the provider trait’s leading context argument, and a tuple of trailing parameters, using
`()` when that tuple is empty.

A const argument in the provider trait’s argument list is rejected because `Params` is a tuple of
types. Const generics on the provider struct are preserved.

---

## Function, getter, and handler macros

Function, getter, and handler macros derive most of their behavior from the annotated Rust item.
Their custom arguments select names:

```ebnf
CgpFnArgs       -> TraitName?      // #[cgp_fn]:       default = fn name in PascalCase
CgpComputerArgs -> ProviderName?   // #[cgp_computer]: default = fn name in PascalCase
CgpProducerArgs -> ProviderName?   // #[cgp_producer]: default = fn name in PascalCase
BlanketTraitArgs -> ContextName?   // #[blanket_trait]: default = __Context__

TraitName    -> IDENTIFIER
ProviderName -> IDENTIFIER
ContextName  -> IDENTIFIER
```

`#[cgp_auto_getter]`, `#[cgp_auto_dispatch]`, and `#[async_trait]` do not accept arguments. Their
behavior comes from the annotated trait and supported companion attributes.

`#[cgp_fn]` puts function generics on the generated trait and impl, keeps ordinary `where` bounds on
the impl, and converts implicit arguments to field reads. It does not generate method-level
generics: parameters written on the function become trait and impl parameters.

`#[cgp_computer]` combines function parameters into one input tuple. Whether the function is async
and whether it returns `Result` determine the base component and promotion bundle. `#[cgp_producer]`
requires a synchronous function without parameters or generics. `#[async_trait]` rewrites async
methods to return `impl Future`. See [functions-and-getters](functions-and-getters.md) and
[handlers](handlers.md) for expansions.

---

## Attribute modifiers

Modifier attributes are interpreted by a host macro; they do not expand independently. The following
table lists their accepted forms, effects, and hosts:

| Attribute | Effect | Host macros |
| --- | --- | --- |
| `#[implicit]` | Replaces an argument with a context-field read | `cgp_fn`, `cgp_impl` |
| `#[uses(Trait, Trait<P>, …)]` | Adds `Self` bounds to the impl | `cgp_fn`, `cgp_impl` |
| `#[extend(Trait, Trait<P>, …)]` | Adds supertraits; also adds impl bounds in `cgp_fn` | `cgp_fn`, `cgp_component` |
| `#[extend_where(Pred, …)]` | Adds predicates to the generated trait's `where` clause | `cgp_fn` |
| `#[impl_generics(Param: Bound, …)]` | Adds bounded parameters only to the impl | `cgp_fn` |
| `#[use_provider(Provider: Trait<…> + …)]` | Inserts the context into inner-provider bounds | `cgp_impl`, `cgp_fn` |
| `#[derive_delegate(Wrapper<Param>)]` | Generates a parameter-keyed dispatcher impl | `cgp_component` |
| `#[prefix(@Path in Namespace)]` | Registers a component path through `RedirectLookup` | `cgp_component` |
| `#[default_impl(Key in NamespacePath)]` | Registers a provider as a namespace default | `cgp_impl` |

`#[implicit]` is a bare marker on an argument with a type and plain identifier, such as
`#[implicit] width: f64`. It rejects `#[implicit(x)]` and `#[implicit = "x"]`. The host removes the
argument, adds the field bound, and binds the value at the start of the body. A mutable implicit
must be the only implicit argument and requires `&mut self`.

`#[uses]` accepts comma-separated bounds and accumulates repeated attributes. Prefer the simple
`Trait<Params>` form. Associated-type equality such as `HasErrorType<Error = AppError>` is also
accepted, but use `#[use_type]` to constrain an abstract type and rewrite its uses together.

`#[extend]` accepts the same simple-path list for public supertraits. It does not apply to
`#[cgp_impl]`, which does not define a trait to extend. `#[extend_where]` instead accepts full
`where` predicates, including associated-type equality. `#[impl_generics]` adds parameters only to
the generated impl, leaving the trait's parameters unchanged.

`#[use_provider]` accepts one provider per attribute. Join several bounds on that provider with `+`,
and use separate attributes for different providers. A comma-separated list of provider-and-trait
pairs fails with `expected +`. The attribute turns a bound such as `AreaCalculator` into
`AreaCalculator<Self>` and adds it to the impl's `where` clause. It does not rewrite the body:
call `Provider::method(self)` explicitly.

`#[derive_delegate]` supports a single dispatch key or a tuple, such as `Wrapper<(A, B)>`. Repeat
the attribute to generate several dispatchers. This is legacy syntax; prefer `open` for new wiring
where applicable. See [wiring](wiring.md).

`#[prefix]` registers a component in a namespace and generates a `RedirectLookup` impl. Repeat it
to register the component in several namespaces.

`#[default_impl]` accepts a type key or an `@`-path key. A type key such as
`String in DefaultImpls1<Component>` names the component in the lookup trait. A path key such as
`@app.GreeterComponent in AppNamespace` binds the prefixed component's own path, so a context can
join without a `for` loop. The namespace path may name any lookup trait with a `Delegate`
associated type; the macro appends the table parameter. Repeat the attribute to register in
several tables.

The check macros carry their own modifiers, covered with them below: `#[check_trait(Name)]` and `#[check_providers(…)]` on a table, `#[check_params(…)]` and `#[skip_check]` on an entry.

### `#[use_type]`

`#[use_type]` imports associated types and rewrites their local names to qualified paths. Its
arguments identify the trait, imported types, and optional source context:

```ebnf
UseTypeArgs  -> UseTypeSpec ( `,` UseTypeSpec )* `,`?

UseTypeSpec  -> TraitPath `.` TypeItems ( `in` ContextPath )?

ContextPath  -> TypePath
TraitPath    -> TypePath

TypeItems    -> UseTypeIdent
              | `{` UseTypeIdent ( `,` UseTypeIdent )* `,`? `}`

UseTypeIdent -> IDENTIFIER ( `as` IDENTIFIER )? ( `=` Type )?
```

Separate the trait path from its associated-type list with `.`. The trait path retains its own `::`
segments and generic arguments. Each imported name can have an `as` alias and an `= Type` equality
constraint. Bare uses of the imported name or alias become `<Target as Trait>::Type`.

The target defaults to `Self`. An `in Types` suffix selects a named type and adds `Types: Trait` as
a `where` bound instead of a supertrait. The reserved keyword `in` separates the target
unambiguously from the preceding type.

Equality constraints are accepted on `#[cgp_fn]` and `#[cgp_impl]`. `#[cgp_component]` accepts
imports but rejects equality constraints because they produce impl-side bounds. See
[abstract-types](abstract-types.md) for aliases, targets, and equality examples.

---

## Wiring and checking macros

Wiring macros select providers, and check macros assert that the selected providers satisfy their
dependencies. Namespaces share wiring across contexts.

### `delegate_components!`

The body is an optional generic list and `new` keyword, a target type, and a brace-delimited table:

```ebnf
DelegateComponents -> Generics? `new`? TargetType `{` TableBody `}`

TargetType    -> Type

TableBody     -> Statement* ( Mapping ( `,` Mapping )* `,`? )?

Statement     -> OpenStmt | NamespaceStmt | ForStmt

OpenStmt      -> `open` ( `{` Type ( `,` Type )* `,`? `}` | Type ) `;`

Mapping       -> Key `:`  ProviderValue
               | Key `->` ProviderValue
               | Key `=>` PathValue

Key           -> SingleKey | MultiKey | PathKey
SingleKey     -> Generics? Type
MultiKey      -> `[` SingleKey ( `,` SingleKey )* `,`? `]`
PathKey       -> Generics? `@` PathHead

PathHead      -> PathSegment ( `.` PathHead )?
               | `[` PathSegment ( `,` PathSegment )* `,`? `]` ( `.` PathHead )?
               | `{` PathHead ( `,` PathHead )* `,`? `}`

PathSegment   -> Generics? Type

PathValue     -> `@` PathSegment ( `.` PathSegment )*

ProviderValue -> Type
               | IDENTIFIER `<` `new` InnerTable `>`

InnerTable    -> IDENTIFIER GenericArgs? `{` TableBody `}`
```

Place every `open`, `namespace`, and `for` statement before mappings. The parser reads statements
first, so one appearing after `Key: Value` fails to parse. A leading generic list applies to the
target table, and `new` also declares the target struct.

Choose the mapping operator according to the lookup required. `:` selects a provider directly. `->`
forwards the same key to another table and adds a `Value: DelegateComponent<Key>` bound. `=>`
redirects along an `@`-path, supporting namespaces and the `open` shorthand. The parser accepts any
operator with any key form, though not every combination is useful.

A key can be a type, a bracketed list of types, or an `@`-path. A list produces a separate entry for
each key. Within paths, brackets and braces have different meanings.

Brackets provide alternatives for one path segment and allow further segments, as in
`@app.[FooComponent, BarComponent].[u64, String]`. Braces provide alternative complete tails and end
the path. They may nest and contain tails of different lengths, as in
`@app.{ErrorRaiserComponent.{&'static str, String}, ErrorWrapperComponent}`. Both forms produce all
combinations with the rest of the path. A `PathValue` on the right of `=>` does not accept groups.

A nested provider value such as `UseDelegate<new Inner { … }>` declares an inner table. This legacy
dispatch syntax supports generic table names such as `BarValue<T>` and wrappers other than
`UseDelegate`.

`open` enables per-value `@Component.Key: Provider` entries directly on the target. Braces are
optional for one component and required for several. Attributes are rejected on both the table and
its entries, with an error at the attribute’s source location. See [wiring](wiring.md).

Each plain `Key: Provider` mapping generates `DelegateComponent<Key>` with `Delegate = Provider` and
a forwarding `IsProviderFor` impl. The latter carries the selected provider’s dependencies through
the target.

`open Component;` delegates the component to `RedirectLookup<Target, PathCons<Component, Nil>>`. A
corresponding `@Component.Value: Provider` entry stores the provider under
`PathCons<Component, PathCons<Value, __Wildcard__>>`. The tail is a generic `__Wildcard__`, so the
entry can answer redirects with additional path segments. At resolution time, `RedirectLookup`
appends the dispatch parameter. `open C;` and `C => @C,` generate the same impl.

### `delegate_and_check_components!`

`delegate_and_check_components!` uses the wiring table grammar and adds attributes for naming the
check trait and controlling individual checks:

```ebnf
DelegateAndCheck -> TableAttr* Generics? `new`? TargetType `{` TableBody `}`

TableAttr        -> `#` `[` `check_trait` `(` IDENTIFIER `)` `]`

TableBody        -> Statement* ( CheckedMapping ( `,` CheckedMapping )* `,`? )?

CheckedMapping   -> EntryAttr? Mapping

EntryAttr        -> `#` `[` `check_params` `(` Type ( `,` Type )* `,`? `)` `]`
                  | `#` `[` `skip_check` `]`
```

The wiring half accepts the same `Mapping`, `Key`, `ProviderValue`, and `Statement` forms as
`delegate_components!`. The checking half derives assertions only for component-name keys:
`SingleKey` or `MultiKey` under `:` or `->`. Path keys, `=>` redirects, and `open`, `namespace`, and
`for` statements remain silently unchecked. Use separate wiring and check blocks for these forms.

The generated check trait defaults to `__CanUse{Context}`, distinct from `check_components!`’s
`__Check{Context}`. Both can therefore appear in one module. Each mapping accepts at most one entry
attribute: `#[check_params(…)]` supplies concrete parameters, while `#[skip_check]` disables its
check. They are mutually exclusive. See [checking](checking.md).

### `check_components!`

`check_components!` accepts one or more tables. Each table names a context and entries to check,
with optional attributes, generics, and a `where` clause:

```ebnf
CheckComponents -> CheckTable+

CheckTable      -> TableAttr* Generics? ContextType WhereClause? `{` CheckEntries `}`

TableAttr       -> `#` `[` `check_trait` `(` IDENTIFIER `)` `]`
                 | `#` `[` `check_providers` `(` Type ( `,` Type )* `,`? `)` `]`

ContextType     -> Type

CheckEntries    -> ( CheckEntry ( `,` CheckEntry )* `,`? )?

CheckEntry      -> CheckKey ( `:` CheckValue )?

CheckKey        -> Type
                 | `[` Type ( `,` Type )* `,`? `]`

CheckValue      -> CheckParam
                 | `[` CheckParam ( `,` CheckParam )* `,`? `]`

CheckParam      -> Generics? Type
```

Omit the entry value for a component without parameters; otherwise, supply the parameters to check.
Arrays of keys or values generate checks for every combination. `#[check_trait(Name)]` overrides the
default `__Check{Context}` name.

Use `#[check_providers(…)]` to assert `IsProviderFor` on each listed provider instead of
`CanUseComponent` on the context. This gives each layer of a higher-order provider its own check
location. See [checking](checking.md).

A check table generates a marker trait for the asserted bound and an empty impl for each entry. The
impl compiles only if the bound holds. A successful build is the passing assertion; the checks do
not run at runtime.

Default checks assert `CanUseComponent<Component, Params>` on the context. With
`#[check_providers(…)]`, they assert `IsProviderFor<Component, Context, Params>` on each named
provider.

### `cgp_namespace!`

The body is an optional generic list and `new`, a namespace name, an optional parent, and an optional table:

```ebnf
CgpNamespace    -> Generics? `new`? NamespaceName ( `:` ParentNamespace )? ( `{` NamespaceBody `}` )?

NamespaceName   -> IDENTIFIER GenericArgs?
ParentNamespace -> TypePath GenericArgs?

NamespaceBody   -> Statement* ( Mapping ( `,` Mapping )* `,`? )?
```

`cgp_namespace!` reuses the wiring mappings, usually `=>` for path redirection or `:` for a direct
provider. The colon in the header names a parent namespace, adding its lookups to the child’s own
entries.

Omit the table when the namespace adds nothing to its parent. `new Child: Parent` generates the
struct, trait, and inheritance impl. Only `{` or the end of input may follow the header. In
contrast, `delegate_components!` always requires braces.

Contexts use the following statements inside their wiring tables to import namespace entries:

```ebnf
Statement     -> NamespaceStmt | ForStmt

NamespaceStmt -> `namespace` IDENTIFIER `;`

ForStmt       -> `for` `<` IDENTIFIER `,` IDENTIFIER `>` `in` TypePath WhereClause?
                 `{` ( NormalMapping ( `,` NormalMapping )* `,`? )? `}`

NormalMapping -> Key `:` ProviderValue
```

`namespace Name;` forwards unresolved lookups through that namespace. A `for` statement binds key
and provider variables from the table named after `in`, then generates the body’s `:` mappings for
those entries. Its optional `where` clause is added to each generated impl. Entry attributes are
rejected. See [namespaces](namespaces.md).

---

## Type-level construction macros

Type-level construction macros encode strings, lists, and paths for CGP lookups. Their inputs are:

```ebnf
SymbolInput  -> STRING_LITERAL

ProductInput -> ( Type ( `,` Type )* `,`? )?          // Product!  (type position)
ProductExpr  -> ( Expression ( `,` Expression )* `,`? )?  // product! (value position)

SumInput     -> ( Type ( `,` Type )* `,`? )?

PathInput    -> `@` PathSegment ( `.` PathSegment )*
PathSegment  -> Type
```

`Symbol!("abc")` expands to `Symbol<3, Chars<'a', Chars<'b', Chars<'c', Nil>>>>`. The leading const
is the byte length, so `Symbol!("世界")` records `6`. It supplies a length that the supported stable
Rust version cannot compute from `Chars` in const position.

`Product![A, B]` expands to `Cons<A, Cons<B, Nil>>`, and `product![…]` constructs the corresponding
value. Empty products use `Nil`. `Sum![A, B]` expands to `Either<A, Either<B, Void>>`, ending in the
uninhabited `Void`.

`Path!(@app.error.FooComponent)` expands to a `PathCons` chain. Lowercase non-primitive segments
become `Symbol!` tags; capitalized or primitive segments remain types. See
[type-level-primitives](type-level-primitives.md).

---

## Derives

Data derives do not accept custom arguments. `HasField`, `HasFields`, `CgpData`, `CgpRecord`,
`CgpVariant`, `BuildField`, `ExtractField`, and `FromVariant` generate code from the annotated
item’s structure. Named struct fields use `Symbol!` tags, and tuple fields use `Index<N>`.

`CgpVariant`, enum `CgpData`, `ExtractField`, and `FromVariant` require one unnamed payload per
variant, as in `Circle(Circle)`. Unit, multi-field tuple, and struct-style variants fail with
“Expected variant to contain exactly one unnamed field”. Wrap a richer payload in a dedicated
struct. See [extensible-data](extensible-data.md) for the derives and their restrictions.

---

## Reading error messages

Determine whether an error comes from macro parsing or Rust type checking. Parser errors usually
identify the rejected input directly. Type errors refer to generated traits and types, which must be
traced back to the original component or wiring.

### Wiring and dependency errors

An `IsProviderFor` failure means the provider cannot satisfy the component for the given context.
For example, `X: IsProviderFor<SomeComponent, Ctx, …>` may fail because a field, abstract type, or
trait implementation is missing. Read the nearby dependency notes and supply the named requirement. Do not
write an `IsProviderFor` impl to suppress the error; the provider macros generate it. See
[components](components.md).

A failed `Ctx: DelegateComponent<SomeComponent>` bound means the context lacks wiring for that
component. Add the delegation entry. A [check](checking.md) distinguishes this from an
`IsProviderFor` failure, where a provider is selected but its dependencies are unsatisfied.

A `CanUseComponent` error reports a failed wiring assertion from `check_components!` or
`delegate_and_check_components!`. Trace the named unmet bound through the provider chain. Some
requirements are ordinary traits without component markers; satisfy those through Rust impls or
bounds rather than wiring entries.

An `overflow evaluating the requirement …` error on a component often indicates a `UseContext`
cycle. If the context delegates a component to `UseContext` and that delegation is its only
implementation, provider and consumer resolution call back into each other. Use `UseContext` as an
inner provider rather than the context’s own delegate for that same component. See
[wiring](wiring.md).

### Decoding printed type-level values

Read the characters in `Symbol<N, Chars<…>>` in order to recover the field name. The leading number
is the length. Other common expanded forms identify different structures: `Cons<…, Cons<…, Nil>>` is
a product list, `Either<…, Either<…, Void>>` is a sum list, and `PathCons<…, …>` is a namespace or
redirect path. See [type-level-primitives](type-level-primitives.md) for the full representations.

### Errors that underline the whole macro block

An error underlining an entire macro invocation may come from one generated entry. Generated tokens
normally retain a source location, but synthesized tokens can fall back to the invocation’s
location. The broad underline does not imply that every entry is wrong.

For `E0119` conflicting impls, look for duplicate wiring entries or overlapping dispatch keys. For
`E0207`, look for a generic parameter in a provider or `#[cgp_fn]` header that is not constrained by
an argument or `where` clause.

### Macro-parser errors

Parser and expansion errors often identify a specific input restriction. Use the diagnostic to
locate the syntax to change:

- **`expected :` near `open`, `namespace`, or `for`:** A statement usually appears after a mapping.
  Move all statements before the mappings.
- **Unsupported entry attribute:** `delegate_components!` and `cgp_namespace!` reject attributes on
  entries. Remove the attribute or use the macro that supports it.
- **Rejected const generic:** Component-trait parameters and provider-trait arguments must fit the
  type-based dispatch representation. An associated `const` item on a trait is allowed.
- **“Expected variant to contain exactly one unnamed field”:** Wrap the variant's payload in one
  unnamed field, using a separate struct for richer data.
- **Default-bodied async method:** `#[async_trait]` does not wrap a default body in `async {}`, so
  that form is unsupported.
- **Generic `#[cgp_auto_dispatch]` method:** Non-lifetime method parameters require a quantified
  bound that Rust cannot express, so the macro rejects them.

---

## Further reference

The topic references explain these grammars through worked examples:

- [Components](components.md): Trait generation and provider impls.
- [Wiring](wiring.md): Delegation tables and dispatch.
- [Checking](checking.md): Assertions and dependency diagnostics.
- [Functions and getters](functions-and-getters.md): Function macros, field access, and modifiers.
- [Abstract types](abstract-types.md): Type components and `#[use_type]`.
- [Higher-order providers](higher-order-providers.md): Inner-provider bounds and calls.
- [Namespaces](namespaces.md): Shared wiring and defaults.
- [Handlers](handlers.md): Computation macros and promotion.
- [Extensible data](extensible-data.md): Data derives and shape restrictions.
- [Type-level primitives](type-level-primitives.md): Strings, lists, and paths.

Fetch the relevant page from the online
[CGP knowledge base](https://github.com/contextgeneric/cgp-knowledge-base/tree/main/cgp) for a
construct's exhaustive syntax, corner cases, and implementing source. The `reference/macros/`
documents contain the Syntax Grammar and Expansion sections used by this reference.
