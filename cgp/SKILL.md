---
name: cgp
description: >-
  Read, write, debug, and explain Context-Generic Programming (CGP) code in Rust.
  Use this skill whenever you encounter or are asked to work with CGP: any code that
  uses `cgp::prelude::*`, the `#[cgp_component]`, `#[cgp_impl]`, `#[cgp_provider]`,
  `#[cgp_fn]`, `#[cgp_type]`, `#[cgp_getter]`, `#[cgp_auto_getter]`, `#[cgp_computer]`,
  `#[cgp_producer]`, or `cgp_namespace!` macros, the `delegate_components!`,
  `check_components!`, or `delegate_and_check_components!` macros, the `Symbol!`,
  `Product!`, `Sum!`, or `Path!` type-level macros, the `HasField`/`HasFields` traits or
  their derives, providers such as `UseContext`/`UseDelegate`/`UseField`/`UseType`, the
  handler family (`Computer`/`Producer`/`Handler`), or terms like consumer trait,
  provider trait, provider, wiring, impl-side dependency, or context-generic. Trigger it
  even when the user does not say "CGP" by name but is clearly working with these
  constructs, when a Rust trait error mentions `IsProviderFor`/`DelegateComponent`, or
  when someone wants modular, dependency-injected, multiple-implementation Rust traits.
---

# Context-Generic Programming (CGP) in Rust

CGP lets Rust contexts choose among interchangeable trait implementations through **wiring**.
It works around coherence restrictions by separating the trait callers use from the trait providers
implement. This primer introduces the vocabulary, core constructs, and macro expansions needed to
read CGP code.

Load the relevant sub-skill before writing, modifying, reviewing, or debugging any construct it
covers. The primer introduces each construct; the `references/` sub-skills supply its exact grammar,
full expansion, corner cases, and worked examples. For example,
[components](references/components.md) explains how `#[cgp_impl]` rewrites `self`, and
[macro-grammar](references/macro-grammar.md) specifies which attribute forms parse. Use the
[sub-skill index](#sub-skills-load-the-one-that-owns-your-task) to find the references your task
requires.

CGP's procedural macros expand to ordinary Rust traits and impls. Understanding those expansions
helps explain how the constructs work and why their errors occur. This primer includes expansions
where they help establish that connection.

## Tooling: use cargo-cgp for readable errors and expansions

Use `cargo-cgp` when it is available to diagnose CGP compile errors. Its `check` command replaces
`cargo check` for diagnosis and rewrites CGP errors into a compact summary that leads with the root
cause. Each rewritten message retains rustc's error code, adds a `[CGP-Exxx]` tag, and shows the
dependency chain. Its [`expand`](#reading-what-a-macro-generated-cargo-cgp-expand) command displays
the generated code. Recommend `cargo-cgp` for checking CGP code, and prefer it when diagnosing a
wiring failure.

Check availability with `cargo cgp --version` or `cargo cgp check` in a CGP project. If the
subcommand is missing, recommend installing it for clearer errors. Install it on the user's behalf
only with their approval: setup provisions a nightly toolchain and builds a compiler-linked driver.

Prefer installation through cargo on most machines. Run `cargo install cargo-cgp`, then
`cargo cgp setup`. Installation builds the small front-end with the existing toolchain; setup uses
rustup to provision the pinned nightly and build its matching driver.

Use Nix only when the host has a `nix` command on `PATH`, the project has a `flake.nix`, or the user
requests it. Otherwise, omit Nix from the recommendation. When Nix is present and `cargo-cgp` is
absent, prefer running it from the project directory without installing it:
`nix run github:contextgeneric/cargo-cgp/v0.1.0-alpha -- check`. Arguments after `--` go to
`cargo check`. To install into a Nix profile, use
`nix profile install github:contextgeneric/cargo-cgp/v0.1.0-alpha`.

The pinned nightly applies only to cargo-cgp's own check, so the project retains its toolchain.
`cargo cgp setup` installs that nightly, or the Nix flake builds it. See the
[installation instructions](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cargo-cgp/reference/installation.md)
for details.

Run `cargo cgp check` wherever you would run `cargo check`. Arguments after `check` are forwarded,
as in `cargo cgp check --workspace`. The
[error-code catalog](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cargo-cgp/error-code.md)
explains the `[CGP-Exxx]` tags.

### Reading what a macro generated: `cargo cgp expand`

Read the macro expansion when a diagnostic leaves the generated impls unclear. `cargo cgp expand`
prints the expanded crate with CGP's type-level constructs restored to readable macro notation.
For example, it displays a field tag as `Symbol!("width")`, a pipeline as
`Product![StepOne, StepTwo]`, and a namespace key as `Path!(@app.GreeterComponent)`.

Use expansion to investigate these questions:

- **Generated types:** Find the impl behind an unfamiliar `IsProviderFor<…>`, `PathCons<…>`, or
  `__Context__` in a diagnostic.
- **Wiring entries:** Inspect the actual `DelegateComponent` keys and `Delegate` values produced by
  a table that does not resolve.
- **Generated bounds:** Check a provider's `where` clauses or a getter's field requirements.
- **Different syntax forms:** Expand and compare forms when only one compiles to locate the
  difference responsible for the failure.

Run it on one target, narrowed to what you care about:

```sh
cargo cgp expand --lib                              # the whole library target
cargo cgp expand --lib --item contexts::MockApp     # one module, type, or trait
```

**Target selection is required when a package has several targets.** Pass `--lib` or `--bin NAME`,
or cargo declines with "extra arguments to `rustc` can only be passed to one target". Other arguments
(`-p`, `--features`) forward to `cargo rustc`. The expansion goes to stdout, so redirect it to a file
when it is long and read that instead of flooding your context.

**`--item <path>` makes the output manageable.** The path is `::`-separated, may carry a leading
`crate::`, and names something inside the crate being expanded. What it names decides what you get:

- a **module** gives its contents (`--item contexts`);
- a **type** gives its declaration and every impl written *for* it. For a context struct that means
  the `HasField`/`HasFieldMut` impls the derive generated, and its `DelegateComponent` wiring entries
  with the real key and provider types (`--item Rectangle`);
- a **trait** gives its definition and every impl *of* it, which is usually the rule you want. Naming
  a component's *provider* trait (`--item AreaCalculator`) gives the provider trait, the delegation
  blanket impl, the `UseContext` and `RedirectLookup` impls, and each wired provider's impl. Naming
  the *consumer* trait (`--item CanCalculateArea`) gives just the consumer trait and its routing
  blanket.

Use `cargo cgp check` to verify wiring. `expand` stops after macro expansion, so it can succeed
on a crate that fails type checking. That makes it useful while debugging, but its success does not
verify the generated impls.

Read the expansion as diagnostic output. It is not intended for compilation: the tool strips the
`cgp::macro_prelude::` qualifier, and an `open` statement's per-key entry retains its raw
`PathCons<…>` key.

`expand` is newer than cargo-cgp v0.1.0-alpha, so a crates.io install does not carry it yet. Until
the next release it comes from the Nix flake without a tag
(`nix run github:contextgeneric/cargo-cgp -- expand --lib`) or from a source checkout. See
<https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cargo-cgp/reference/installation.md>.

**Scope:** cargo-cgp is optional and adds only `check` and `expand`. It does not provide
`cargo cgp build`, `run`, or `test`, so build, run, and test the project with plain cargo. CGP itself
compiles on any **stable Rust ≥ 1.89**, so plain `cargo check` works on a CGP project too. Reach for
`cargo cgp check` when you hit or expect a wiring error and want it made readable.

`cargo-cgp` can also be Rust Analyzer's on-save check backend, via
`rust-analyzer.check.overrideCommand` set to
`["cargo","cgp","check","--workspace","--all-targets","--message-format=json"]`. But **never modify
the user's Rust Analyzer settings implicitly.** Mention this option and let them opt in. Edit their
editor configuration only when they ask you to.

When cargo-cgp is not available, or leaves an error largely unrewritten, read the raw compiler
output by hand. Only then load the [error-extraction sub-skill](references/error-extraction.md), the
technique for reducing a raw CGP cascade to its root cause. When cargo-cgp has reshaped the error,
its `[CGP-Exxx]` headline and root-cause tree are already the compact summary that sub-skill would
produce, so you do not need it.

### Versions and keeping this skill current

This skill is written for **CGP v0.8.0** and **cargo-cgp v0.1.0-alpha**. Check both on the host and
act on a mismatch:

- Read the user's `cgp` version from its `Cargo.toml` or `Cargo.lock` entry, and run
  `cargo cgp --version` for the tool.
- **If either is older than recorded here**, recommend updating it so its behavior matches this
  skill: `cargo update -p cgp` for the library, and `cargo cgp update` (or a Nix flake refresh) for
  the tool.
- **If the host's `cgp` is newer than v0.8.0**, this skill is behind the library. Tell the user the
  **skill should be upgraded** to match their `cgp`, rather than changing their code to fit an older
  skill. Treat the newer `cgp` as authoritative and flag the gap instead of guessing.

## The problem CGP solves

CGP lets contexts select different implementations of the same interface despite Rust's coherence
restrictions. Rust permits at most one implementation of a trait for a given type, and its orphan
rule forbids implementing a foreign trait for a foreign type. Those rules limit interchangeable
implementations and downstream choices for types a crate does not own.

CGP separates the caller's interface from the provider's implementation to allow those choices.
A provider trait uses a marker type owned by the implementing crate as `Self`. A concrete context
then selects that provider through a type-level table. The choice belongs to the context, so
different contexts can select different implementations of the same interface.

## Blanket traits and impl-side dependencies

An impl-side dependency is a constraint required by an implementation but absent from its trait
interface. CGP uses these dependencies for dependency injection. The technique starts with ordinary
blanket trait implementations, also called extension traits. Here, the `CanGreet` implementation
requires `HasName`, while the trait itself does not:

```rust
pub trait CanGreet {
    fn greet(&self);
}

pub trait HasName {
    fn name(&self) -> &str;
}

impl<Context> CanGreet for Context
where
    Context: HasName,
{
    fn greet(&self) {
        println!("Hello, {}!", self.name());
    }
}
```

`CanGreet` hides its `HasName` dependency inside the blanket impl, so a caller that is itself
generic does not have to forward `HasName` the way it would with a free generic function. In CGP
you typically start by writing generic logic as a blanket trait like this, and promote it to a
full CGP component only when you need more than one implementation. Blanket traits are not
themselves CGP components, but the technique recurs throughout CGP.

## The core vocabulary

CGP separates the interface callers use from the implementation a context selects. The following
terms describe those roles:

- **Consumer trait:** The ordinary `self`-style trait callers use, such as `CanGreet` or
  `CanCalculateArea`. Its name describes an action (`CanDoX`).
- **Provider trait:** The interface generated by `#[cgp_component]`, with `Self` moved to an explicit
  `Context` parameter, as in `Greeter<Context>`. Its name is a noun such as `SomethingDoer`, or uses
  the `Provider` suffix when a noun does not fit.
- **Provider:** A zero-sized marker struct, such as `GreetHello`, that implements a provider trait.
  It exists as a type-level name and is never instantiated.
- **Wiring:** A type-level table that selects a provider for each component on a context.
- **Impl-side dependency:** A provider's `where`-clause constraint that the consumer trait does not
  expose.
- **Component:** The generated bundle of consumer trait, provider trait, and `…Component` marker
  used as the wiring key.

Callers use consumer traits, and providers implement provider traits. Generated blanket impls
connect them: wiring a context to a provider makes the context implement the consumer trait.
A provider method's `context: &Context` serves the same role as the consumer method's `&self`.

Do not call any of these a **capability**. What a component, a `#[cgp_fn]` function, or a getter
defines is a *trait*; the thing a caller invokes is a *method* or an *operation*; what `#[uses]`
imports is a *trait dependency*; and a `#[cgp_fn]` or `#[blanket_trait]` trait that is not a
component is a *blanket trait*. The word "capability" names a different construct in the
object-capability model and in Rust's context-and-capabilities proposal, so using it for CGP's
own constructs misleads readers who know either. Use it only when describing those other systems.

A context can hold the data being operated on or implement the traits an operation needs.
A **value context** is the data, such as `String` in `String: CanEncode` or `Rectangle` in
`Rectangle: CanCalculateArea`. An **environmental context** carries the wiring choices and implements
the traits an application, test harness, or service relies on. Environmental contexts are more common
in CGP code and
may be fieldless: `struct App;` can exist solely to carry wiring. Both kinds occupy the `Self`
position and carry a wiring table, so their signatures do not distinguish them.

A component's target determines what its methods operate on. A self-targeted component acts on
`Self`, as in `CanGreet`, `HasErrorType`, and getters. A parameter-targeted component acts on a type
parameter while `Self` selects the implementation, as in `CanEncodeValue<Value>` or
`CanCalculateArea<Shape>`. A parameter can also select wiring: in `CanCompute<Code, Input>`,
`Input` is the target and `Code` is a selector.

The context and target together determine how many independent provider choices are available.
A self-targeted component wired on a foreign value type has one provider program-wide; authors can
define additional environmental contexts to make independent choices. Consult
[modularity-hierarchy](references/modularity-hierarchy.md) when choosing an arrangement. When
explaining CGP, identify the arrangement in the example because a change from value context to
environmental context may leave the signature unchanged.

Inside a provider, `self` and `Self` in `#[cgp_impl]` refer to the context. The raw provider-trait
form names them `context` and `Context`. The provider struct is only a type-level name, so it cannot
store state or supply fields at runtime.

## Reading CGP code on sight

Most CGP code is readable once you recognize a handful of shapes:

- `#[cgp_component(Greeter)] trait CanGreet { fn greet(&self); }` defines a component. `CanGreet`
  is the consumer trait you call, `Greeter<Context>` is the provider trait implementations target,
  and `GreeterComponent` is the wiring key.
- `#[cgp_impl(new GreetHello)] #[uses(HasName)] impl Greeter { fn greet(&self) { … } }` writes a
  provider named `GreetHello` for the `Greeter` component. Inside, `self`/`Self` mean the
  *context*, and `#[uses]` lists the impl-side dependencies. It desugars to `where Self: HasName`,
  the form you read in older code.
- `#[cgp_fn] fn rectangle_area(&self, #[implicit] width: f64, #[implicit] height: f64) -> f64 { … }`
  defines a trait with a single blanket implementation, pulling `width`/`height` from
  the context's fields automatically.
- `delegate_components! { Person { GreeterComponent: GreetHello } }` wires the `Person` context. It
  says "for the `Greeter` component, `Person` uses the `GreetHello` provider." After this, `Person`
  implements `CanGreet`.
- `check_components! { Person { GreeterComponent } }` is a compile-time assertion that the wiring is
  complete and all transitive dependencies are satisfied.

A consumer trait can also be implemented directly on a context like any normal Rust trait
(`impl CanGreet for Person { … }`). CGP traits are a superset of vanilla traits, and the macros
only save boilerplate.

## Choosing a construct

Prefer the modern forms in this table when writing CGP. Explicit forms remain useful for reading
generated code and legacy implementations, and some advanced cases still require them. See
[Writing providers](#writing-providers) for exceptions and
[modern-idioms](references/modern-idioms.md) for complete before-and-after examples.

| To… | Prefer | Not (legacy / advanced / read-only) |
|---|---|---|
| write a provider | `#[cgp_impl]`, header `impl Trait` (omit `for Context`) | raw `#[cgp_provider]` / `#[cgp_new_provider]` |
| read a field from your own context | an `#[implicit]` argument | `#[cgp_auto_getter]` / any getter trait declared just to read it |
| declare a getter (field on *another* type, or a named accessor other code requires) | `#[cgp_auto_getter]`, used sparingly | `#[cgp_getter]` (only for per-context field choice) |
| require a trait on the context | `#[uses(Trait)]` | `where Self: Trait` |
| require an inner provider | `#[use_provider(P: Trait)]` | `where P: Trait<Self>` |
| name an abstract type (e.g. `Error`) | `#[use_type(Trait.Type)]` + the bare alias | `: Trait` supertrait + `Self::Type` |
| pass several args to `#[uses]` / `#[use_type]` | one attribute, comma-separated | repeating the same attribute |
| bind several inner providers with `#[use_provider]` | one attribute per provider | a comma-separated list of pairs (it does not parse) |
| add a supertrait that contributes methods | `#[extend(Trait)]` | native `pub trait …: Supertrait` |
| dispatch a component per type | the `open` statement (or a namespace) | `#[derive_delegate]` + `UseDelegate<new …>` tables |
| verify a context is fully wired | separate `check_components!` (or `delegate_and_check_components!` for a basic starter context) | leaving a context's wiring unchecked |
| build a field/list/string/path type | `Symbol!` / `Product!` / `Sum!` / `Path!` sugar | hand-written `Cons`/`Nil`/`Chars`/`Either`/`PathCons` |

Some names are gone entirely, not merely dated. Never write `#[cgp_context]`, which was removed
(assemble a context with `delegate_components!` and the derives instead), or `ProvideType`, which
was renamed to `TypeProvider`. One caveat carries across the whole table: a construct's *own* local
associated type stays qualified as `Self::Output`. Only an *imported* abstract type is written bare
via `#[use_type]`.

## The prelude and version

Almost everything CGP exports comes through one import, which belongs at the top of every module
that uses CGP:

```rust
use cgp::prelude::*;
```

Import traits and markers outside the prelude from their defining modules. Missing imports can
prevent otherwise valid CGP code from compiling. These modules contain names that commonly need
explicit imports:

| Import from | What lives there |
|---|---|
| `cgp::core::field::traits` | `TakeField`, `FinalizeExtractResult`, `StaticString`, `AppendProduct`, `ConcatProduct`, `MapFields`, `TransformMap`, `TransformMapFields`, `MapField`, `FieldMapper` |
| `cgp::core::field::impls` | the casts `CanUpcast`, `CanDowncast`, `CanDowncastFields`, `CanBuildFrom`, and the markers `IsOptional` and `IsOwned` |
| `cgp::core::base::traits` | `StaticFormat` (and `cgp::core::base::types` for `Chars`, `Cons`, `Nil`, `PathCons`, `Symbol`) |
| `cgp::core::component` | `DefaultImpls1`, `DefaultImpls2` |
| `cgp::core::error` / `cgp::extra::error` | the error wiring keys, and the backend providers |
| `cgp::extra::monad::traits` | `MonadicBind`, `ContainsValue`, `LiftValue`, `MonadicTrans` |
| `cgp::extra::field::impls` | the whole optional-field layer: `HasOptionalBuilder`, `ToOptional`, `SetOptional`, `FinalizeOptional`, `CanFinalizeWithDefault`, `CanBuildWithDefault` |

Check imports for casts and optional-field traits because neither group is in the prelude.
Related names can also differ: `ConcatPath` and `DefaultNamespace` are in the prelude, while
`StaticString`, `StaticFormat`, `DefaultImpls1`, and `DefaultImpls2` are not. Among the builder
traits, `TakeField` requires an explicit import.

This skill describes CGP **v0.8.0** and cargo-cgp **v0.1.0-alpha**. See
[Tooling](#tooling-use-cargo-cgp-for-readable-errors-and-expansions) for checking both versions on
the host and reconciling a mismatch. Inside documentation code blocks you may omit the prelude
import for brevity.

---

## Components

`#[cgp_component]` generates the traits and wiring support that separate calling a trait's methods
from implementing them. Apply it to the consumer trait that callers will use:

```rust
#[cgp_component(Greeter)]
pub trait CanGreet {
    fn greet(&self);
}
```

The macro emits `CanGreet` unchanged, so callers write `person.greet()`. It also generates the
provider trait with `Self` moved to a leading `Context` parameter and `self` renamed to `context`:

```rust
pub trait Greeter<Context>: IsProviderFor<GreeterComponent, Context, ()> {
    fn greet(context: &Context);
}
```

The **component marker** `pub struct GreeterComponent;` is the zero-sized key into the wiring table.
The **blanket impls** connect the sides. One makes any context that implements the provider trait
*for itself* implement the consumer trait. The other lets a context that delegates this component
(via `DelegateComponent`) inherit the provider trait from whatever provider it delegates to. You
never write these blanket impls. They are the routing machinery, and it is enough to think of wiring
as a table lookup.

That lookup is resolved **entirely at compile time**. The table is a set of trait impls, so the
compiler picks the provider during type resolution and monomorphizes the call to a direct, statically
dispatched one. CGP wiring is therefore zero-cost. "Table lookup" is a useful mental model, but the
generated code involves neither a runtime table nor dynamic dispatch nor a vtable. In real generated
code the context parameter is named `__Context__` and the provider parameter `__Provider__`, reserved
identifiers chosen so they never clash with your types. The names `Context`/`Provider` here are for
readability.

The attribute's argument sets the generated names. The bare `#[cgp_component(Greeter)]` form names
only the provider trait. The component marker defaults to that name plus `Component`
(`GreeterComponent`) and the context to `__Context__`. A key/value form with brace delimiters
overrides any of them, as in
`#[cgp_component { name: GreeterComponent, provider: Greeter, context: Context }]`, where only
`provider` is required. One limitation to know: a **const generic parameter** on the trait is
rejected, because a component's extra parameters are recorded as a tuple of *types* in
`IsProviderFor`, and a const value has nowhere to live there. An associated `const` *item* on the
trait is fine, and a const-generic provider struct supplies it as usual. See
[macro-grammar](references/macro-grammar.md) for the full argument grammar and
[components](references/components.md) for the complete expansion.

A component trait can contain as many methods, associated types, and consts as an ordinary Rust
trait. Group items when one provider choice determines their implementation. A method and its
associated output type can form one such choice, as in `CanCompute` and `CanHandle`. A getter
component can group several field reads that one `UseFields` provider supplies by name.

Combining independent choices in one component reduces provider reuse. For example, a `Shape`
trait with `area`, `perimeter`, `scale`, and `rotate` requires each provider to satisfy all methods'
dependencies. A higher-order provider must forward methods it does not change, and a context using
only part of the interface may need placeholder types and `unimplemented!()` bodies for the rest.

Check whether another context could reuse a provider's complete implementation. A consumer trait
named after an entity rather than an action can signal unrelated choices grouped together. If the
provider would not be reusable, implement the trait directly on the concrete context. See
[components](references/components.md) for multi-item examples, reuse costs, and how to split a
component.

### `IsProviderFor` and error messages

`IsProviderFor<Component, Context, Params>` is an empty marker trait used as a supertrait on
every provider trait. Its only purpose is good error messages. A provider lists its dependencies in
a `where` clause, and the macros implement `IsProviderFor` for the provider under the *same* bounds.
So when a dependency is unmet, the compiler can name the missing bound instead of vaguely saying
"the trait is not implemented." When you see an error that some provider does not implement
`IsProviderFor<…>`, read it as "the provider trait is not implemented, because the named dependency
is missing." You never write `IsProviderFor` yourself. The provider macros generate it.

### Writing providers

Prefer `#[cgp_impl]` when writing a provider. It accepts consumer-style method signatures with
`self` and `Self`, then rewrites them into the provider-trait form:

```rust
#[cgp_impl(new GreetHello)]
#[uses(HasName)]
impl Greeter {
    fn greet(&self) {
        println!("Hello, {}!", self.name());
    }
}
```

The attribute names the provider, and `new` also declares `struct GreetHello;`. The
[`#[uses(HasName)]`](#uses-extend-extend_where) attribute generates the impl-side bound
`where Self: HasName`.

Prefer `impl Greeter` and let the macro insert the context parameter. Use the explicit
`impl<Context> Greeter for Context` form only when you must name or bound the context, such as for
a lifetime or higher-ranked trait bound the shorthand cannot express. Declare that context in the
impl generics. In either form, `self` and `Self` mean the context.

The example expands to a provider-trait impl with an explicit context parameter:

```rust
#[cgp_new_provider]
impl<Context> Greeter<Context> for GreetHello
where
    Context: HasName,
{
    fn greet(context: &Context) {
        println!("Hello, {}!", context.name());
    }
}
```

The lower-level provider macros accept explicit provider-trait impls. `#[cgp_provider]` preserves
an impl on an existing provider struct and generates `IsProviderFor` with the same `where` bounds.
`#[cgp_new_provider]` also declares the provider struct. Generic providers receive a `PhantomData`
field over their parameters, as in `pub struct Multiply<Field>(PhantomData<Field>);`. The attribute
can override the component name, which defaults to the provider trait's name plus `Component`.

`#[cgp_impl(Self)]` emits a direct consumer-trait impl on a concrete context. This form requires
`for Context` and bypasses the provider rewrite while still applying companion attributes such as
`#[use_provider]`.

Use these modern forms by default, with explicit syntax only where the attributes cannot express
the required bounds:

- **Providers:** Write `#[cgp_impl]` with an `impl Greeter` header, omitting `for Context`.
- **Dependencies:** Use [`#[uses]`](references/functions-and-getters.md) for trait dependencies and
  [`#[use_provider]`](references/higher-order-providers.md) for inner providers.
- **Field access:** Prefer [`#[implicit]`](references/functions-and-getters.md) for fields on the
  provider's context, including fields read by several providers. Use getter traits for access on
  other types, named accessors other code requires, or associated types inferred from fields.
- **Method supertraits:** Use [`#[extend]`](references/functions-and-getters.md).
- **Abstract types:** Import them with [`#[use_type]`](references/abstract-types.md) and use the bare
  alias, including in `#[cgp_component]` definitions.
- **Per-type dispatch:** Use `open` or a namespace when defining new components.

Combine multiple `#[uses]` or `#[use_type]` arguments in one comma-separated attribute, as in
`#[uses(A, B)]` or `#[use_type(T.X, U.Y)]`. Each `#[use_provider]` binds one provider, so use a
separate attribute for each binding.

Use `#[use_type]`'s equality form to fix an abstract type to a concrete type. For example,
`#[use_type(HasErrorType.{Error = AppError})]` replaces
`where Self: HasErrorType<Error = AppError>`. This form works on `#[cgp_impl]` and `#[cgp_fn]` but
is rejected on `#[cgp_component]`. The right-hand side is also substituted, so an abstract type can
be defined in terms of another imported type; see [abstract-types](references/abstract-types.md).

Keep explicit bounds where the attributes cannot express the dependency. Equality bounds on traits
you would not import types from, such as `Iterator<Item = u8>` or `From<X>`, remain in `where`
clauses. A lifetime or higher-ranked trait bound (HRTB) may require a named context. A trait's own
associated type remains qualified as `Self::Output`; only imported abstract types use bare aliases.
Load [modern-idioms](references/modern-idioms.md) when reading or modernizing existing CGP for the
complete mapping between explicit and modern forms.

The provider's `where` clause is where **impl-side dependencies** live, whether you write it by hand
or let `#[uses]` generate it. `GreetHello` requires `Self: HasName`, but `CanGreet` does not expose
that bound, so a caller bounding on `CanGreet` never sees `HasName`. The wiring satisfies each
dependency by resolving it through the same context.

A consumer trait is still an ordinary trait. When you do not need multiple implementations, write
`impl CanGreet for Person { … }` directly and skip the provider machinery.

---

## Wiring: connecting a context to providers

Wiring records, on a context type, which provider supplies each component. The underlying mechanism
is the `DelegateComponent` trait, a type-level table whose key is the `…Component` marker and whose
`Delegate` associated type is the chosen provider. You almost always write it through
`delegate_components!`:

```rust
#[derive(HasField)]
pub struct Person {
    pub name: String,
}

delegate_components! {
    Person {
        GreeterComponent: GreetHello,
    }
}
```

After this, `Person` implements `CanGreet`, and `person.greet()` resolves through the table to
`GreetHello`. Swapping the table entry is the only change needed to swap behavior.

The macro has a few shorthands. An **array key** maps several components to one provider:
`[FooComponent, BarComponent]: FooBarProvider`. A leading **`new`** keyword
(`delegate_components! { new MyComponents { … } }`) also defines `struct MyComponents;`. This is how
you build an **aggregate provider**, a zero-sized provider that holds a table dispatching each
component to a sub-provider, so other contexts can delegate a whole group of components to it as one
reusable unit. A leading **generic list** (`delegate_components! { <T> MyContext<T> { … } }`) wires a
whole family of contexts at once.

Further **operators** stand where the `:` does, and you will meet them when reading real wiring.
`Key -> OtherTable` forwards the key to *that table's* own entry for the same key instead of naming a
provider. `Key => @path` redirects the lookup along a type-level path, and the `open` statement
below is its sugared special case. Those operators, the `@`-path key forms, and the `namespace` and
`for` statements belong to one shared body grammar that `cgp_namespace!` and
`delegate_and_check_components!` reuse in full. [wiring](references/wiring.md) and
[macro-grammar](references/macro-grammar.md) carry it, and all of the forms combine inside a single
block.

The target of `delegate_components!` is therefore not always a context. It is either a concrete
context (as `Person` is above) or an aggregate provider (as `MyComponents` is). This distinction
governs checking. An aggregate provider is dispatched *to* by contexts and is never its own context,
so it must be wired with plain `delegate_components!` and never `delegate_and_check_components!`.
The next section explains why.

To understand what wiring *does*, picture the explicit version. `delegate_components!` is
equivalent to implementing the consumer trait by hand and forwarding to the provider:
`impl CanGreet for Person { fn greet(&self) { <GreetHello as Greeter<Person>>::greet(self) } }`.
The macro generates the forwarding impls and propagates `IsProviderFor`.

### `UseContext`

`UseContext` is a provider that implements a provider trait by routing back through the context's
*own* consumer-trait impl, the dual of the consumer blanket impl. Wiring a component to `UseContext`
means "use whatever this context already does for this trait," which is mainly useful as the default
inner provider of a higher-order provider (below). Delegating a component directly to `UseContext`
when the context's only implementation of that component *is* that delegation creates a circular
dependency and fails to compile.

### Dispatching a generic-parameter component per type with `open`

When a component is generic over a type parameter, you often want a different provider per value of
that parameter. The modern, preferred way is the **`open` statement** inside `delegate_components!`.
Given a component `CanCalculateArea<Shape>` (provider `AreaCalculator`), a context dispatches per
shape like this:

```rust
delegate_components! {
    MyApp {
        open AreaCalculatorComponent;

        @AreaCalculatorComponent.Rectangle: RectangleArea,
        @AreaCalculatorComponent.Circle: CircleArea,
    }
}
```

Place `open` statements before plain `Component: Provider` mappings or the macro will fail to
parse. Use `open AreaCalculatorComponent;` for one component or `open { A, B };` for several.
Each `@Component.Key: Provider` entry assigns a provider to one value of the dispatch parameter.

Choose path grouping by what the alternatives represent. Braces group complete path tails and
end the path, as in `@AreaCalculatorComponent.{u32, u64, bool}: SomeProvider`. Brackets group
alternatives for one segment and allow further segments:
`@app.[FooComponent, BarComponent].[u64, String]: P` creates every combination. Keys may carry
generics, as in `@SomeComponent.<'a, T> &'a T: SomeProvider`.

`open` uses the `RedirectLookup` impl generated by `#[cgp_component]`, so it does not need an
extra component attribute. It does not combine with a joined namespace (`#[prefix(...)]`); use the full namespace
feature for that arrangement.

**Legacy form (read but don't write):** older code dispatches the same way by wrapping a nested
table in the `UseDelegate` provider, as in
`AreaCalculatorComponent: UseDelegate<new AreaCalculatorComponents { Rectangle: RectangleArea, Circle: CircleArea }>`,
generated by a `#[derive_delegate(UseDelegate<Shape>)]` attribute on the component. This still works
and is common in existing code, but it is slated for deprecation, so prefer `open` for new code.
Some CGP-shipped components (the error and handler families) are still *defined* with
`#[derive_delegate]` in the library, so you will see `UseDelegate` tables wiring them.

---

## Checking: verifying wiring at compile time

CGP wiring is **lazy**. Defining a `delegate_components!` entry does not itself check that the
provider's transitive dependencies are satisfied. A missing dependency therefore surfaces only when
the consumer trait is finally used, often as a confusing error. To catch it early and clearly, assert
the wiring with a check:

```rust
check_components! {
    Person {
        GreeterComponent,
    }
}
```

This generates a check trait whose supertrait is `CanUseComponent<GreeterComponent, ()>` for
`Person`. If `Person` cannot use the component, the compiler reports the missing dependency at this
site, walking through `IsProviderFor` so the real cause (such as a missing
`HasField<Symbol!("name")>`) is named rather than hidden. For a component with generic parameters,
list the parameter after the component (`GreeterComponent: Rectangle`), group multiple parameters as
a tuple (`(Rectangle, f64)`), and use array syntax to check several at once.

`delegate_and_check_components!` fuses wiring and checking in one step, so every delegation is
verified the moment it is written:

```rust
delegate_and_check_components! {
    Person {
        GreeterComponent: GreetHello,
    }
}
```

Its check trait is named `__CanUse{Context}` (versus `__Check{Context}` for `check_components!`), so
both macros can appear once per module without clashing. Override the name with
`#[check_trait(Name)]`. When the delegated component has generic parameters, add
`#[check_params(...)]` on the entry. Skip a single entry's check with `#[skip_check]`.

Use `delegate_and_check_components!` for basic wiring or a starter context. It helps newcomers
avoid omitting checks and encountering delayed wiring errors. It derives checks only for plain
`Component: Provider` entries, so advanced mappings need more control.

Keep `delegate_components!` and `check_components!` separate in larger or more advanced codebases.
Separate checks support `open` and namespaced wiring, concrete parameters for generic keys, and
`#[check_providers(...)]` assertions for individual provider layers. Every context's wiring must be
checked regardless of which macro is used.

Wire aggregate providers with plain `delegate_components!`. An aggregate provider supplies
implementations to other contexts, so checking it as a context with `delegate_and_check_components!`
asks the wrong question. The check passes vacuously if its providers need nothing from the context,
or blames the aggregate for fields and types that the actual context would supply. Verify the
aggregate through a real context that delegates to it, or use `#[check_providers(...)]` to assert
`IsProviderFor` directly.

Not every unsatisfied bound is a CGP component. Some are ordinary or blanket traits that
`check_components!` cannot verify, and those must be satisfied by ordinary Rust means.

For a nested [higher-order provider](references/higher-order-providers.md), checking the context
tells you a layer is broken but not which one. The `#[check_providers(...)]` attribute on a
`check_components!` table changes the assertion from `CanUseComponent` on the context to
`IsProviderFor` on each named provider. A dependency missing only from the outer wrapper then errors
on its line alone, while one missing from the inner provider errors on both, which pinpoints the
layer. See [checking](references/checking.md) for debugging instructions.

---

## Functions and getters

Most basic CGP reads and writes values from the context, and the constructs here make that look like
plain Rust.

### `HasField` and `#[derive(HasField)]`

`HasField<Tag>` is tag-keyed field access. The `Tag` is a type-level name: `Symbol!("width")` for a
named field or `Index<0>` for a tuple field. `#[derive(HasField)]` generates one impl per field:

```rust
#[derive(HasField)]
pub struct Rectangle {
    pub width: f64,
    pub height: f64,
}
// generates HasField<Symbol!("width"), Value = f64> and HasField<Symbol!("height"), Value = f64>
```

Field values are read with `self.get_field(PhantomData::<Symbol!("width")>)`. The `PhantomData`
carries the tag so type inference knows which field is meant.

### `#[cgp_fn]` and `#[implicit]` arguments

`#[cgp_fn]` turns one function into a single-implementation blanket-impl trait, the simplest entry
point to CGP. Arguments marked `#[implicit]` are removed from the signature and pulled from context
fields via `HasField`:

```rust
#[cgp_fn]
fn rectangle_area(&self, #[implicit] width: f64, #[implicit] height: f64) -> f64 {
    width * height
}
```

This generates a `RectangleArea` trait (named from the function in PascalCase, or `#[cgp_fn(MyName)]`
to override) with a blanket impl for any context that has `width: f64` and `height: f64` fields.
Implicit arguments get `.clone()` added for owned values and `.as_str()` for `&str`. Generic
parameters on the function move to the trait and impl, and the `where` clause becomes impl-side
dependencies on the impl only. Generic *method* parameters are intentionally unsupported. Prefer
implicit arguments for basic code, because they make CGP look like ordinary functions.

### `#[uses]`, `#[extend]`, `#[extend_where]`

`#[uses(TraitA, TraitB<Param>)]` (on `#[cgp_fn]` or `#[cgp_impl]`) imports `Self` trait bounds, read
like a `use` statement. The simple `Trait<Params>` form is idiomatic, but any `where`-clause bound is
accepted, including associated-type equality (`HasErrorType<Error = AppError>`). For abstract-type
pins, prefer `#[use_type]`'s equality form:

```rust
#[cgp_fn]
#[uses(RectangleArea)]
fn scaled_rectangle_area(&self, #[implicit] scale_factor: f64) -> f64 {
    self.rectangle_area() * scale_factor * scale_factor
}
```

`#[extend(Trait)]` adds supertrait bounds to the generated trait. It is the only way to add
supertraits in `#[cgp_fn]`, where ordinary `where` clauses declare impl-side dependencies. It is
also the preferred form for a non-type supertrait on `#[cgp_component]`: the attribute
presents the trait dependency directly.

Use `#[use_type]` for an abstract-type supertrait whose associated type appears in the signatures.
It adds the supertrait and rewrites uses of the type.

`#[extend_where(Bound)]` adds `where` clauses to a `#[cgp_fn]` trait definition. It accepts arbitrary
predicates, including associated-type equality, beyond the forms accepted by `#[uses]` and
`#[extend]`.

`#[impl_generics(Param: Bound)]` adds a bounded parameter only to the impl generated by `#[cgp_fn]`.
Use it when a function body borrows a generic value that should not become a trait parameter.
For example, `#[impl_generics(Name: Display)]` can support an `#[implicit] name: &Name` argument.

### Getters: `#[cgp_auto_getter]`, `#[cgp_getter]`, `UseField`

Prefer `#[implicit]` arguments for reading fields from the provider's own context. They cover
fields shared by several providers and borrow plain `&T` arguments without cloning.

Use getter traits sparingly, for the cases implicit arguments cannot express:

- **Access on another type:** Take that type as the first argument, as in
  `fn foo_bar(foo: &Self::Foo) -> &Self::Bar`, called as `App::foo_bar(&foo)`, or require a getter
  bound such as `Request: HasBasicAuthHeader<Self>`.
- **Named accessor:** Expose an accessor that other code requires through a bound such as
  `#[uses(HasName)]` or a supertrait.
- **Abstract field type:** Declare an associated return type inferred from the field, keeping its
  concrete type hidden from callers.

`#[cgp_auto_getter]` generates a blanket getter impl over `HasField`, with the field name taken from
the method name. It is the getter form to prefer for those cases:

```rust
#[cgp_auto_getter]
pub trait HasName {
    fn name(&self) -> &str;
}
// blanket impl for any context with a `name` field; &str/&String shorthands handled
```

A single-getter trait may instead declare a local associated type used as the return type, inferred
from the field: `trait HasName { type Name; fn name(&self) -> &Self::Name; }`.

`#[cgp_getter]` is an **advanced** tool, reserved for when a context needs full control over which
field a getter reads from. Most getters should use `#[cgp_auto_getter]` or an implicit argument
instead. It is like `#[cgp_component]` but also provides a `UseField<Tag>` blanket impl, so the
getter's source field can be chosen by *wiring* rather than fixed to the method name. The
`UseField<Tag>` provider implements a getter by reading the field named `Tag`, which may differ from
the method name:

```rust
delegate_components! {
    Person {
        NameGetterComponent: UseField<Symbol!("first_name")>,
    }
}
// Person::name() now returns the `first_name` field
```

`UseFieldRef` is the `AsRef`/`AsMut`-based variant. Any getter can also be implemented by hand. The
macros only save boilerplate.

---

## Abstract types

CGP abstracts over types with associated types in components. `#[cgp_type]` is the dedicated macro,
so use it instead of `#[cgp_component]` for an abstract-type trait:

```rust
#[cgp_type]
pub trait HasNameType {
    type Name;
}
```

This defaults the provider name to the type name plus `TypeProvider` (here `NameTypeProvider`,
marker `NameTypeProviderComponent`) and also generates a `UseType` blanket impl. A context fixes the
type by wiring the component to `UseType<ConcreteType>`:

```rust
delegate_components! {
    Person {
        NameTypeProviderComponent: UseType<String>,
    }
}
// or directly: impl HasNameType for Person { type Name = String; }
```

The direct impl is just as valid, and it shows that abstract types are ordinary associated-type
traits.

The `#[use_type(HasScalarType.Scalar)]` attribute is the recommended way to *use* an abstract type
inside `#[cgp_fn]`, `#[cgp_impl]`, or `#[cgp_component]`. It rewrites bare `Scalar` to the fully
qualified `<Self as HasScalarType>::Scalar` everywhere and adds the supertrait or `where` bound,
removing `Self::` boilerplate and ambiguity. CGP's built-in abstract-type component is `HasType`
(provider `TypeProvider`).

---

## Higher-order providers

A **higher-order provider** takes another provider as a generic parameter and constrains it with a
provider-trait bound, so its inner behavior is chosen by wiring rather than fixed:

```rust
#[cgp_impl(new ScaledAreaCalculator<InnerCalculator>)]
#[use_provider(InnerCalculator: AreaCalculator)]
impl<InnerCalculator> AreaCalculator {
    fn area(&self, #[implicit] scale_factor: f64) -> f64 {
        let base_area = InnerCalculator::area(self);
        base_area * scale_factor * scale_factor
    }
}
```

`#[use_provider(InnerCalculator: AreaCalculator)]` completes the inner provider's bound by adding the
`Self` parameter for you (you write `: AreaCalculator`, and it means `AreaCalculator<Self>`) and
moves it into the `where` clause. That is the *only* thing the attribute does. Inside the body you
still call the provider explicitly with the associated-function form `InnerCalculator::area(self)`.
The attribute does not rewrite the call site. A context then chooses the inner provider when wiring,
for example `AreaCalculatorComponent: ScaledAreaCalculator<RectangleAreaCalculator>`.

A higher-order provider often defaults its inner parameter to `UseContext`
(`pub struct IterSumArea<Inner = UseContext>(PhantomData<Inner>);`), so that when an inner provider
is not named, the inner step falls back to the context's own wiring. Not every provider with a generic
parameter is higher-order. A provider like `GetName<Tag>` that uses `Tag` only as a `HasField` key,
without a provider-trait bound, is not.

When a component itself is generic (`#[cgp_component(AreaCalculator)] trait CanCalculateArea<Shape>`),
the provider trait appends the parameters after the context (`AreaCalculator<Context, Shape>`),
`IsProviderFor` groups them into its `Params` tuple, and lifetimes are lifted into the `Life<'a>`
type. Such a component is most useful for **cross-context dependencies**. When the main target is a
generic parameter (`CanCalculateArea<Shape>: HasScalarType`), individual shape types need not
implement the shared traits. The common context supplies the shared abstract type, value-level
injection (a global scale factor via a getter), and lazy per-context provider binding, so two apps
can wire the same shape to different providers.

---

## Error handling

CGP makes the error type abstract, so generic code can fail without naming a concrete error.
`HasErrorType` (an abstract-type component, `type Error: Debug`) gives a context one shared error
type. `CanRaiseError<SourceError>` constructs it from a concrete source error
(`Context::raise_error(source)`), and `CanWrapError<Detail>` attaches detail. Both build on
`HasErrorType` and are associated-function (without `self`) components that dispatch per source or
detail type. An error-aware trait imports the error type with `#[use_type(HasErrorType.Error)]`, so
it names the error as the bare `Error` instead of writing `: HasErrorType` and `Self::Error` by hand:

```rust
#[cgp_component(Loader)]
#[use_type(HasErrorType.Error)]
pub trait CanLoad {
    fn load(&self, path: &str) -> Result<String, Error>;
}

#[cgp_impl(new LoadOrFail)]
#[uses(CanRaiseError<String>)]
#[use_type(HasErrorType.Error)]
impl Loader {
    fn load(&self, path: &str) -> Result<String, Error> {
        if path.is_empty() {
            return Err(Self::raise_error("empty path".to_owned()));
        }
        Ok(format!("contents of {path}"))
    }
}
```

A context wires its error type and the raise/wrap behavior. The backend providers plug in per source
type, modern-style with `open`. They are `RaiseFrom` (convert via `From`), `ReturnError`,
`RaiseInfallible`, `PanicOnError`, `DebugError`/`DisplayError` (format into a `String` and forward),
and `DiscardDetail`:

```rust
delegate_components! {
    App {
        open ErrorRaiserComponent;

        ErrorTypeProviderComponent: UseType<String>,
        @ErrorRaiserComponent.String: RaiseFrom,
        @ErrorRaiserComponent.ParseError: DebugError,
    }
}
```

**Imports:** `HasErrorType`, `CanRaiseError`, and `CanWrapError` come from the prelude. The wiring
keys (`ErrorTypeProviderComponent`, `ErrorRaiserComponent`, `ErrorWrapperComponent`) live under
`cgp::core::error`, and the backend providers (`RaiseFrom`, `DebugError`, …) under
`cgp::extra::error`, so import the specific names you wire. Standalone backends (`cgp-error-anyhow`,
`cgp-error-eyre`, `cgp-error-std`) provide ready error types.

---

## Handlers: the computation family

CGP models computation as a family of components along the axes of synchronous versus async,
infallible versus fallible, and input-taking versus input-free:

- **`Computer` / `CanCompute`** is a synchronous, infallible transform `compute(&self, PhantomData<Code>, input) -> Output`. By-reference (`ComputerRef`) and async (`AsyncComputer`) variants exist.
- **`TryComputer` / `CanTryCompute`** is the fallible computer.
- **`Producer` / `CanProduce`** is input-free production (only a context and a `Code` tag).
- **`Handler` / `CanHandle`** is the general **async, fallible, error-aware** computation, used for I/O and pipelines. It requires `HasErrorType` as a supertrait.
- **`CanRun` / `CanSendRun`** are task runners.

Any CGP trait with async methods, whether a handler, a runner, or one you define, declares them under
the `#[async_trait]` attribute. The attribute rewrites each `async fn` to `-> impl Future`, the
lint-clean, allocation-free form. The generated future does not carry a `Send` bound, so spawning it
on a work-stealing executor needs the `Send`-recovery pattern in [handlers](references/handlers.md).

`#[cgp_computer]` and `#[cgp_producer]` define a `Computer`/`Producer` provider from a function.
Providers compose through combinators. `PipeHandlers<Product![A, B, C]>` chains handlers left to
right, `ComposeHandlers` nests them, `ReturnInput` passes input through, and the `Promote*` adapters
lift a simpler handler (such as a sync `Computer`) into a more capable one (an async `Handler`). For
example, a context wires a pipeline of field-reading computers:

```rust
delegate_components! {
    MyContext {
        ComputerComponent:
            PipeHandlers<Product![
                Multiply<Symbol!("foo")>,
                Add<Symbol!("bar")>,
                Multiply<Symbol!("baz")>,
            ]>,
    }
}
// context.compute(PhantomData::<()>, 5) runs ((5*foo)+bar)*baz
```

Dispatch routes an extensible-data input to per-variant handlers. `#[cgp_auto_dispatch]` generates a
handler from a trait, and the combinators `MatchWithHandlers`, `MatchWithValueHandlers`, and
`ExtractFieldAndHandle` match an enum's variants to sub-handlers, proving exhaustiveness without a
wildcard. Monadic handlers (`PipeMonadic`, `BindOk`, `BindErr`, the identity/ok/err monads) compose
handlers through a monad. The handler family is broad, so read [handlers](references/handlers.md)
for the full set, including `Send`-bound recovery for async trait methods.

---

## Extensible data

CGP can build and read structs and enums generically, by their named fields and variants. The
`#[derive(HasFields)]` derive exposes a type's whole field list. `#[derive(CgpData)]`, and the
record- or variant-specific `CgpRecord`/`CgpVariant`, derive the full extensible-data machinery:

```rust
#[derive(CgpData)]
pub struct Person {
    pub first_name: String,
    pub last_name: String,
}
```

The extensible builder pattern constructs records field by field through `HasBuilder` and
`BuildField`. It assembles a context from independent outputs for each field. The underlying field
list uses `Product![A, B, C]`, represented by `Cons` and `Nil`.

The extensible visitor pattern handles each variant of an enum. `FromVariant` constructs variants,
and the `ExtractField` family deconstructs them. Variant lists use `Sum![A, B]`, represented by
`Either` and `Void`. The handler dispatch combinators described above route variant inputs to their
handlers.

Structural casts convert between data shapes. `CanUpcast` widens a smaller enum into a larger one,
`CanDowncast` narrows an enum, and `CanBuildFrom` rebuilds a record from a superset of its fields.

---

## Namespaces

Namespaces provide reusable wiring tables that can inherit from a parent. Define one with
`cgp_namespace! { new MyNs: ParentNs { … } }`, omitting the parent when inheritance is unnecessary.
A context joins it with `namespace MyNs;` inside `delegate_components!`. Lookups without a direct
context entry forward through the namespace, so direct entries override individual keys.

Register a component in a namespace with `#[prefix(@path in MyNs)]` on its `#[cgp_component]`
trait. A `#[cgp_impl]` provider registers a per-type default through
`#[default_impl(T in DefaultImpls1<Component>)]`. The context imports those defaults with a
`for <T, Provider> in Table { … }` loop.

The underlying mechanism is the `RedirectLookup` provider, which re-routes a component lookup along
a type-level `Path!`. The `open` statement above is a lightweight special case of it.
`DefaultNamespace` resolves a default provider when a context does not override one. Read
[namespaces](references/namespaces.md) for the preset and inheritance syntax.

---

## Type-level primitives

CGP encodes lists, strings, and numbers as types. Use the shorthand macros when writing code, and
recognize their expanded forms when reading errors:

- **`Symbol!("name")`** is a type-level string (field-name tag). It expands to `Symbol<4, Chars<'n', Chars<'a', Chars<'m', Chars<'e', Nil>>>>`. The leading length works around missing const-generics.
- **`Product![A, B, C]`** is a type-level list. It expands to `Cons<A, Cons<B, Cons<C, Nil>>>`. `product![…]` is the value-level form. Used for field lists and handler pipelines.
- **`Sum![A, B]`** is a type-level sum (the dual of `Product!`), over the `Either`/`Void` list. Used for enum variant lists.
- **`Index<N>`** is a type-level natural number, and tags tuple-struct fields.
- **`Field`** is a value paired with its type-level name tag.
- **`Path!`** / `PathCons` is a type-level path, used by namespaces and `RedirectLookup`.
- **`Life<'a>`** is a lifetime lifted into a type, used when a component has lifetime parameters.
- **`MRef`** is an owned-or-borrowed value.

Prefer the shorthand macros (`Symbol!`, `Product!`) and readable type names (`Cons`/`Nil`) when
writing code.

---

## Sub-skills: load the one that owns your task

Load each sub-skill that applies before reading, writing, reviewing, or debugging code in its
area. These references provide exact grammar, expansions, corner cases, and worked examples beyond
the primer. Load all relevant references when a task spans several areas, follow their cross-links,
and reload a reference when entering an unfamiliar part of the topic.

Start with [macro-grammar](references/macro-grammar.md) whenever writing, editing, or debugging CGP
syntax. It defines the accepted macro forms, the invariants their expansions preserve, and how to
interpret compiler errors involving `IsProviderFor` and `DelegateComponent`.

Load [modern-idioms](references/modern-idioms.md) when reading or modernizing existing CGP. It maps
explicit and legacy forms to current syntax, including provider impls, handwritten `where` bounds,
`Self::Type` paths, and `UseDelegate` tables.

Choose the remaining references by task:

- **[Components](references/components.md):** Load before writing components or providers. Covers
  the complete `#[cgp_component]` expansion, `IsProviderFor`, provider macros, the meaning of
  `self`/`Self`, and how component grouping affects reuse.
- **[Wiring](references/wiring.md):** Load before wiring a context. Covers `DelegateComponent`,
  `delegate_components!` forms, `open`, direct consumer impls, `UseContext` cycles, legacy
  `UseDelegate` tables, and adapters such as `WithProvider`, `WithField`, `WithType`, `WithContext`,
  and `UseDefault`.
- **[Checking](references/checking.md):** Load when wiring fails to compile. Explains lazy wiring,
  check traits, `CanUseComponent`, and the `#[check_trait]`, `#[check_providers]`, `#[check_params]`,
  and `#[skip_check]` options for locating missing dependencies.
- **[Error extraction](references/error-extraction.md):** Load only when `cargo-cgp` is unavailable
  or leaves an error largely unrewritten; see [Tooling](#tooling-use-cargo-cgp-for-readable-errors-and-expansions)
  first. Covers summarizing raw errors, distinguishing hidden from surfaced causes, confirming a
  cause through a signature line, and delegating error reading to a sub-agent.
- **[Functions and getters](references/functions-and-getters.md):** Load for field access and
  function-style traits. Covers `HasField`, `#[cgp_fn]`, implicit access and its borrowing
  rules, dependency attributes, getter macros, `UseField`/`WithField`, and `ChainGetters`.
- **[Abstract types](references/abstract-types.md):** Load for associated-type abstraction. Covers
  `#[cgp_type]`, `HasType`/`TypeProvider`, `UseType`/`UseDelegatedType` wiring, `#[use_type]` imports,
  and `WithType`/`WithDelegatedType` adapters.
- **[Higher-order providers](references/higher-order-providers.md):** Load before composing
  providers. Covers inner-provider bounds, the context parameter, `#[use_provider]`, explicit
  provider calls, `UseContext` defaults, generic components, and cross-context dependencies.
- **[Error handling](references/error-handling.md):** Load for fallible CGP code. Covers
  `HasErrorType`, raising and wrapping errors, backend providers, and which imports come from the
  prelude, `cgp::core::error`, or `cgp::extra::error`.
- **[Handlers](references/handlers.md):** Load for computation and I/O pipelines. Covers the
  computation families, function and dispatch macros, combinators, monadic handlers,
  `HasRuntime`/`HasRuntimeType`, and `Send` recovery for async methods.
- **[Extensible data](references/extensible-data.md):** Load for generic struct and enum operations.
  Covers data derives, builders, extractors, optional and defaulted fields, product and sum lists,
  `AppendProduct`/`ConcatProduct`/`MapFields`, structural casts, exhaustiveness, and the single-payload
  variant rule.
- **[Namespaces](references/namespaces.md):** Load for grouped or inherited wiring. Covers
  `cgp_namespace!`, joining and iterating namespaces, `#[prefix]`, `#[default_impl]`,
  `RedirectLookup`, `Path!`, and `DefaultNamespace`.
- **[Type-level primitives](references/type-level-primitives.md):** Load to interpret nested types
  in errors and expansions. Covers symbols, product and sum lists, `Index`, `Field`, paths, `Life`,
  `MRef`, and `StaticFormat` recovery traits.
- **[Modularity hierarchy](references/modularity-hierarchy.md):** Load when deciding how much CGP
  a problem needs. Compares plain blanket traits through per-provider wiring and identifies the
  coherence restrictions each approach avoids.

### Exhaustive online reference

For the exact macro expansion of any construct, every accepted syntax form, corner cases, or the
implementing source, consult the online knowledge base at
**https://github.com/contextgeneric/cgp-knowledge-base**. CGP's own section is
[`cgp/`](https://github.com/contextgeneric/cgp-knowledge-base/tree/main/cgp), whose `reference/`,
`concepts/`, `guides/`, and `errors/` directories are the authoritative, exhaustive record, and the
worked [`examples/`](https://github.com/contextgeneric/cgp-knowledge-base/tree/main/examples) sit at
the base's top level beside it. The base also documents `cargo-cgp`, under
[`cargo-cgp/`](https://github.com/contextgeneric/cgp-knowledge-base/tree/main/cargo-cgp). Fetch the
relevant page when a detail is not covered here. Do not assume a local copy exists, because this
skill is deployed on its own.

---

## Instructions for explaining CGP to users

Assume basic Rust knowledge and unfamiliarity with CGP unless the user indicates otherwise.
For code changes, add explanations only when asked. When explaining, introduce advanced Rust
concepts such as generics, traits, blanket impls, and coherence as needed, along with unfamiliar
functional or type-level programming concepts.

Explain wiring as choosing a provider from a table. Keep `IsProviderFor`, `DelegateComponent`, and
generated blanket impls out of the explanation unless the user asks about internals. Say "trait",
"method", or "operation" for what a component or `#[cgp_fn]` defines, never "capability", per
[The core vocabulary](#the-core-vocabulary). Familiar
analogies can help explain type-level tables, lists, and strings, but make their limits explicit:
CGP resolves wiring at compile time and generates direct static calls. If comparing it to a vtable,
state that CGP resolves calls statically, without a runtime table, dynamic dispatch, or lookup cost.

State that component traits can contain multiple items whenever component grouping comes up.
Single-method examples must not imply a macro restriction: component traits can contain methods,
associated types, and consts just as ordinary Rust traits can. `CanCompute` and `CanHandle`, for
example, define an associated `Output` alongside their method. Present grouping as the author's
choice about provider reuse, following [components](references/components.md).

When asked to explain a specific piece of code, look up the definitions it depends on before
answering. To explain a `delegate_components!` entry, find the consumer and provider traits behind
the component key and the body of the provider it maps to. To explain a provider, read its own
definition and the definitions of every trait in its `where` clause. To explain how a context
implements something, follow its wiring to see which providers are chosen and trace a method call
through them. For instance, if `NameGetterComponent` is wired to `UseField<Symbol!("first_name")>`,
then a `self.name()` call inside another provider returns the context's `first_name` field.
