# Handlers

CGP handlers provide reusable computations selected through wiring. They differ in whether they are
synchronous or async, can fail, and consume or borrow their input. Producers supply values without
input, while runners execute tasks. This reference covers those components, function macros,
composition, dispatch, and `Send` bounds.

The examples use CGP v0.8.0 and assume `use cgp::prelude::*;`. Each handler is an ordinary
[component](components.md): a consumer trait for callers, a provider trait for implementations, and
a marker selected through [wiring](wiring.md). The prelude carries every handler marker, the
promotion bundles, and the provider traits except `ComputerRef`, `TryComputerRef`, and `HandlerRef`.
The consumer traits, those three provider traits, and the one-step combinators (`Promote`,
`PromoteAsync`, `PromoteRef`, `TryPromote`, `ReturnInput`, `ComposeHandlers`, `PipeHandlers`) come
from `cgp::extra::handler`. A concrete context that delegates a handler also implements its provider
trait, so calling `App::compute(&app, …)` by bare name is ambiguous (`E0034`) when the consumer
trait and that provider trait are both in scope; use method syntax or name the consumer trait.

## The shared shape and the axes

A handler maps a context, `Code` tag, and input to an output type selected by its provider. `Code`
is carried as `PhantomData<Code>` and lets one context select different handlers for different tags.
`Output` is an associated type, so callers do not fix it as a generic parameter.

Choose the simplest handler form that expresses the computation, then use promotion combinators when
a caller needs a more general form. The family distinguishes synchronous from async execution,
infallible from fallible results, and owned from borrowed inputs. Async forms return futures,
fallible forms return `Result<Output, Error>` using [`HasErrorType`](abstract-types.md), and `*Ref`
forms take `&Input`. Promotion can adapt simpler behavior to these interfaces without requiring the
original provider to implement them all.

The main families cover different computation requirements. `Computer` is synchronous and
infallible; `TryComputer` adds failure; and `Handler` combines async execution with failure.
`AsyncComputer` and borrowed variants cover the corresponding intermediate forms. `Producer` takes
only a context and tag, while `CanRun` and `CanSendRun` execute named tasks.

## The computation components

Start with `CanCompute` for synchronous, infallible computation. Its method consumes the input and
returns the provider’s chosen `Output`:

```rust
#[cgp_component(Computer)]
#[derive_delegate(UseDelegate<Code>)]
#[derive_delegate(UseInputDelegate<Input>)]
pub trait CanCompute<Code, Input> {
    type Output;
    fn compute(&self, _code: PhantomData<Code>, input: Input) -> Self::Output;
}
```

The generated provider trait is `Computer<Context, Code, Input>`, with marker `ComputerComponent`.
A context dispatches it by `Code`, by `Input`, or by both with the `open` statement, whose path keys
take one segment per parameter; see [wiring](wiring.md#dispatching-on-a-later-parameter). The
`#[derive_delegate]` attributes keep the legacy `UseDelegate` and `UseInputDelegate` tables working
for existing code.

`AsyncComputer`/`CanComputeAsync` declares `async fn compute_async` under `#[async_trait]`.
`ComputerRef` and `AsyncComputerRef` borrow `&Input`. These infallible components do not require
`HasErrorType`.

`CanTryCompute` supports synchronous computation that may fail. It requires `HasErrorType`, allowing
providers to return the context’s abstract error without selecting an error backend:

```rust
#[cgp_component(TryComputer)]
#[derive_delegate(UseDelegate<Code>)]
#[derive_delegate(UseInputDelegate<Input>)]
#[use_type(HasErrorType.Error)]
pub trait CanTryCompute<Code, Input> {
    type Output;
    fn try_compute(&self, _code: PhantomData<Code>, input: Input)
        -> Result<Self::Output, Error>;
}
```

A `TryComputer` provider carries a `Context: HasErrorType` bound and typically converts a concrete source error into the abstract one with [`CanRaiseError`](error-handling.md). `TryComputerRef` is the by-reference sibling.

`CanHandle` supports async computation that may fail. Generic pipeline code can use this bound for
providers promoted from `Computer`, `AsyncComputer`, or `TryComputer`:

```rust
#[async_trait]
#[cgp_component(Handler)]
#[derive_delegate(UseDelegate<Code>)]
#[derive_delegate(UseInputDelegate<Input>)]
#[use_type(HasErrorType.Error)]
pub trait CanHandle<Code, Input> {
    type Output;
    async fn handle(&self, _tag: PhantomData<Code>, input: Input)
        -> Result<Self::Output, Error>;
}
```

A function bounded by `Context: CanHandle<Code, Input>` accepts any wired computation regardless of which traits the underlying provider depends on. `HandlerRef` borrows the input.

`CanProduce` creates a value without input. It takes a context and `Code` tag, supports tag-based
delegation, and does not require `HasErrorType`:

```rust
#[cgp_component(Producer)]
#[derive_delegate(UseDelegate<Code>)]
pub trait CanProduce<Code> {
    type Output;
    fn produce(&self, _code: PhantomData<Code>) -> Self::Output;
}
```

Use a producer for pipeline inputs such as constants or context-derived defaults. Promotion adapts
it to input-taking handlers by ignoring their input.

Handler providers use the ordinary provider structure. For example, built-in `UseField<Tag>`
implements `Computer` by forwarding computation to the value in the context’s tagged field. The
combinators below compose and adapt these providers.

## Task runners: `CanRun` and `CanSendRun`

Use runners for tasks that return `Result<(), Error>` rather than transforming input. `CanRun<Code>`
is the async interface, and `CanSendRun<Code>` exposes a `Send` future for spawning:

```rust
#[cgp_component(Runner)]
#[async_trait]
#[derive_delegate(UseDelegate<Code>)]
#[use_type(HasErrorType.Error)]
pub trait CanRun<Code> {
    async fn run(&self, _code: PhantomData<Code>) -> Result<(), Error>;
}

#[cgp_component(SendRunner)]
#[async_trait]
#[derive_delegate(UseDelegate<Code>)]
#[use_type(HasErrorType.Error)]
pub trait CanSendRun<Code> {
    fn send_run(&self, _code: PhantomData<Code>)
        -> impl Future<Output = Result<(), Error>> + Send;
}
```

A context can select task providers by `Code`. With `RunnerComponent` delegated to a tag-keyed
`UseDelegate` table, `app.run(PhantomData::<ActionA>)` and `app.run(PhantomData::<ActionB>)` select
different providers. A runner uses `HasRuntime` for runtime access. See [recovering `Send`
bounds](#recovering-send-bounds) for the `CanSendRun` pattern.

## The runtime: `HasRuntimeType` and `HasRuntime`

CGP keeps runtime access abstract so code can use a production executor, a test mock, or another
runtime selected by its context. `HasRuntimeType` defines the associated `Runtime` type, chosen
through [abstract-type wiring](abstract-types.md). `HasRuntime` requires that type and exposes
`fn runtime(&self) -> &Self::Runtime`.

Require `HasRuntimeType` when code only needs to name the runtime’s types. Require `HasRuntime` when
it needs the runtime value to perform operations such as spawning, sleeping, opening sockets, or
reading the clock.

## Defining handlers from functions

`#[cgp_computer]` generates a computation provider from a function and uses promotion to support the
other handler forms. This function becomes the `Add` provider:

```rust
#[cgp_computer]
fn add(a: u64, b: u64) -> u64 {
    a + b
}
```

The provider name defaults to the function’s PascalCase name. Override it with an argument such as
`#[cgp_computer(MyAdder)]`. Parameters become one input tuple, and the return type becomes `Output`.

The macro preserves the function and generates a base provider impl that destructures the input
tuple. It also generates a delegation table that selects promotion providers for the remaining
handler components:

```rust
#[cgp_new_provider]
impl<__Context__, __Code__> Computer<__Context__, __Code__, (u64, u64)> for Add {
    type Output = u64;
    fn compute(_context: &__Context__, _code: PhantomData<__Code__>,
        (arg_0, arg_1): (u64, u64)) -> Self::Output {
        add(arg_0, arg_1)
    }
}
// delegate_components! routes the rest of the family to PromoteComputer<Self>
```

The function signature determines the base provider and promotion bundle. A synchronous function
uses `Computer`; an async function uses `AsyncComputer`. A `Result` return remains the base
provider’s `Output`, while its promotion bundle exposes success and failure through fallible
components.

The signature selects these generated forms:

| Function signature | Base provider | Promotion bundle |
| --- | --- | --- |
| Synchronous, plain return | `Computer` | `PromoteComputer` |
| Synchronous, `Result` return | `Computer` with `Result` output | `PromoteTryComputer` |
| Async, plain return | `AsyncComputer` | `PromoteAsyncComputer` |
| Async, `Result` return | `AsyncComputer` with `Result` output | `PromoteHandler` |

The `Result` check reads the tokens: only a return type written `Result<T, E>` selects a fallible
bundle. `core::result::Result<T, E>` and `anyhow::Result<T>` are treated as plain values, so
`try_compute` wraps them in `Ok`, and a one-argument alias written `Result<T>` fails with
``expected `,` ``. Write the full `Result<T, E>` in a fallible computer's signature. The fallible
bundles pass the `Err` through unconverted, so `E` must be the context's `HasErrorType::Error`, or
the fallible members fail with `E0271`.

Generic parameters and `where` bounds are preserved on the provider impl. A `&Value` parameter
becomes a borrowed entry in the input tuple, and `PromoteRef` entries support the `*Ref` components.
The generated `Add` provider can therefore serve `compute`, `try_compute`, `compute_async`, and
`handle`.

`#[cgp_producer]` generates a `Producer` from a function without arguments and uses
`PromoteProducer` to support the other handler forms:

```rust
#[cgp_producer]
fn magic_number() -> u64 {
    42
}
```

Producer functions must be synchronous and have neither parameters nor generics. The generated
`MagicNumber` provider returns `42` through `produce` and the promoted computation interfaces.
`PromoteProducer` ignores the supplied input for `compute`, `try_compute`, `handle`, and their
borrowed forms.

## Composing and promoting with handler combinators

Handler combinators compose and adapt providers. They are zero-sized providers from `cgp-handler`,
with inner provider types carried in `PhantomData`.

`ComposeHandlers<ProviderA, ProviderB>` runs `ProviderA`, then passes its output to `ProviderB`.
Each stage must support the requested handler form. Fallible forms stop on an error with `?`, and
async forms await each step.

`PipeHandlers<Providers>` extends composition to a `Product!` list. It constructs a right-nested
composition, so `PipeHandlers<Product![A, B, C]>` becomes
`ComposeHandlers<A, ComposeHandlers<B, C>>` and executes `A`, then `B`, then `C`:

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
// input 5 over foo=2, bar=3, baz=4 -> ((5 * 2) + 3) * 4
```

`ReturnInput` returns its input unchanged, ignoring the context and tag. Fallible forms wrap the
input in `Ok`. Use it as a placeholder stage that preserves the result of surrounding computations.

Promotion combinators adapt an inner provider to another handler interface. `Promote<Provider>`
handles conversions such as producer to computer, computer to fallible computer, and async computer
to handler. It supplies the missing behavior by ignoring input or wrapping successful output in
`Ok`.

`PromoteAsync<Provider>` adapts synchronous execution to an async interface. `PromoteRef<Provider>`
adapts value and reference interfaces through dereferencing or reborrowing. `TryPromote<Provider>`
converts between a `Result`-valued `Computer` and `TryComputer` in either direction, and likewise
between a `Result`-valued `AsyncComputer` and `Handler`.

Prefer promotion bundles when wiring several related interfaces. `PromoteComputer`,
`PromoteTryComputer`, `PromoteProducer`, `PromoteAsyncComputer`, and `PromoteHandler` are delegation
tables that select the appropriate adapters for a base provider. The function macros use these
bundles automatically, passing `Self`. A bundle expects its parameter to be a provider wired to that
same bundle, because some entries reach the base through a sibling component: `PromoteComputer<P>`
answers `Handler` through `PromoteAsync<P>`, which needs `P: TryComputer`. To lift a hand-written
provider without wiring it to a bundle, chain the single-step adapters, as in
`PromoteAsync<Promote<MyComputer>>` for a `Handler` from a `Computer`, or
`PromoteAsync<TryPromote<MyCheckedComputer>>` from a `Computer` returning `Result`. The `*Ref`
entries also need a base that accepts a borrow as its input; a base over an owned `u64` answers none
of them.

## Dispatching over extensible data

Dispatch combinators select handlers from an [extensible-data](extensible-data.md) type’s fields or
variants. Enum dispatch runs the handler for the current variant, while record dispatch builds
fields through their providers. The same generic dispatcher can therefore work with several data
types.

Use `#[cgp_auto_dispatch]` to extend a trait’s payload implementations to extensible enums
containing those payloads. The macro generates a blanket impl that forwards each variant to its
payload’s impl:

```rust
#[cgp_auto_dispatch]
pub trait HasArea {
    fn area(&self) -> f64;
}
// with impls for Circle and Rectangle, and a #[derive(CgpData)] enum Shape,
// HasArea is now implemented for Shape too:
let shape = Shape::Rectangle(Rectangle { width: 2.0, height: 2.0 });
assert_eq!(shape.area(), 4.0);
```

Each method generates a per-variant computer named `Compute` plus the method name, from a helper
function that takes the method's own name in the module. The enum impl uses
`MatchWithValueHandlersRef` for `&self`, `MatchWithValueHandlersMut` for `&mut self`, and
`MatchWithValueHandlers` for `self`, with the `MatchFirstWith…` forms when the method takes extra
arguments; an async method keeps the same matcher and bounds it as an `AsyncComputer`. Avoid a
supertrait on the trait, a method needing two distinct lifetimes, and a module item sharing a
method's name: each makes the expansion fail to compile.

Methods cannot have non-lifetime generic parameters because the generated impl would need a
quantified bound Rust cannot express. Use dispatch combinators directly for those methods.

`MatchWithHandlers<Handlers>` converts an enum input to an extractor and runs the supplied
per-variant adapters. It also has borrowed, mutable, and `MatchFirstWith…` forms.
`ExtractFieldAndHandle<Tag, Provider>` tries one variant, `HandleFieldValue` removes the `Field`
wrapper before invoking a computer, and `DowncastAndHandle` routes a group of variants to another
matcher.

Matching stops at the first successful extraction. Each miss excludes a variant from the remainder,
and an uninhabited final remainder proves exhaustiveness without a wildcard: a list that misses a
variant fails on `__PartialShape<IsVoid, IsPresent>: FinalizeExtract`.
`MatchWithValueHandlers<Provider>` builds the adapter list automatically from the enum’s field list,
and `MatchWithFieldHandlers<Provider>` does the same but passes each payload as a
`Field<Tag, Value>`, whose tag names the variant. Both apply to enums only, not structs.

The matchers implement only `Computer` and `AsyncComputer`. To fill a fallible slot, lift the
matcher: `TryComputerComponent: Promote<M>` and `HandlerComponent: PromoteAsync<Promote<M>>`, or
`TryPromote<M>` when the per-variant handlers return `Result`. The borrowed value matchers also
route the fallible components, but those entries do not resolve.

Dispatch by input type with `open` and a two-segment path key. The `open` redirect appends both
`Code` and `Input` to the lookup path, and a per-key generic `<Code> Code` first segment matches
every code, so these entries assign payload computations and an enum matcher by input alone:

```rust
delegate_components! {
    App {
        open ComputerComponent;

        @ComputerComponent.<Code> Code.[Circle, Rectangle]: ComputeArea,
        @ComputerComponent.<Code> Code.Shape: MatchWithValueHandlers,
    }
}
```

The table sends `Circle` and `Rectangle` to `ComputeArea`, while `Shape` uses the matcher, which
routes each payload back through the context's own wiring. A bracketed segment lets several inputs
share one provider. See [wiring](wiring.md#dispatching-on-a-later-parameter) for the key forms and
the one overlap rule.

**Legacy form (read but don't write):** older code wires the same dispatch through a nested
`UseInputDelegate` table. It still works, since the handler components keep
`#[derive_delegate(UseInputDelegate<Input>)]`:

```rust
ComputerComponent:
    UseInputDelegate<new AreaComputers {
        [Circle, Rectangle]: ComputeArea,
        [Shape]: MatchWithValueHandlers,
    }>,
```

`BuildWithHandlers<Output, Handlers>` constructs a record by passing an empty builder through field
adapters, then finalizing it. `BuildAndSetField<Tag, Provider>` computes one field, and
`BuildAndMerge<Provider>` merges a source record’s fields. Each step's provider receives a reference
to the partial record, which implements `HasField` for the fields already set, so a later step can
read an earlier one's field; order the list accordingly. Finalization requires every field to be
present, so an omitted field handler causes a compile error.
`BuildAndMergeOutputs<Output, Providers>` takes a list of providers that each build a sub-record and
wraps each in `BuildAndMerge`, the form the extensible builder pattern uses. The builders implement
`Computer`, `TryComputer`, and `Handler`, and ignore their input, so call them with `()`.

## Composing through a monad

Use monadic handlers when a step’s result determines whether a pipeline continues. The monad selects
which branch passes a value to the next step and which returns immediately.
`PipeMonadic<M, Providers>` combines a monad marker with a `Product!` list to form a computation
provider:

```rust
PipeMonadic::<ErrMonadic, Product![Increment, Increment, Increment]>::compute(&context, code, 253)
// 253 -> Ok(254) -> Ok(255) -> Err("overflow"); the third overflow becomes the output
```

Choose the monad marker according to the branch that should stop the pipeline. `IdentMonadic` passes
every value onward, matching ordinary `PipeHandlers`. `ErrMonadic` continues on `Ok` and stops at
the first `Err`, like `?`. `OkMonadic` continues on `Err` and stops at the first `Ok`, supporting
retry-until-success and variant matching.

`OkMonadicTrans<M>` and `ErrMonadicTrans<M>` combine result branching with a base monad. For
example, a pipeline over `Result<Result<T, E>, F>` can stop on the outer error while passing the
inner result onward.

`BindOk<M, Cont>` and `BindErr<M, Cont>` supply the individual steps that `PipeMonadic` composes.
They can also appear directly in a `PipeHandlers` list. `BindErr` runs `Cont` on an `Ok` value and
stops on `Err`; `BindOk` does the reverse.

Monadic pipelines also support fallible and async-fallible components. They convert each provider
through `TryPromote`, apply `M` as a transformer over `ErrMonadic` (`M: MonadicTrans<ErrMonadic>`,
so the outer error layer is `ErrMonadic`'s), and wrap the result again. Calls
through `try_compute` or `handle` therefore stop on the context’s error type as well.

## Recovering `Send` bounds

An async trait method does not promise callers a `Send` future. `#[async_trait]` rewrites it to
return an unboxed `impl Future` without a `Send` bound. An executor that moves suspended tasks
between threads needs that guarantee when spawning.

Return Type Notation would express the required bound as `handle(..): Send`. The stable Rust version
covered by this skill does not support that notation, so a separate trait must state the stronger
return type.

Declare a companion trait whose method explicitly returns `impl Future + Send`:

```rust
pub trait CanHandleApiSend<Api>:
    CanHandleApi<Api, Request: Send, Response: Send> + Send + Sync
{
    fn handle_api_send(&self, _api: PhantomData<Api>, request: Self::Request)
        -> impl Future<Output = Result<Self::Response, Self::Error>> + Send;
}
```

The companion is an ordinary trait that adds a stronger future bound without changing wiring.
Implement it for each concrete context and API pair. A generic blanket impl cannot prove that the
opaque future returned by `handle_api` is `Send`, even when wrapped in an async block.

For a concrete pair, wiring resolves to a concrete future whose auto-traits the compiler can check.
This impl forwards the call and compiles only when that future is `Send`:

```rust
impl CanHandleApiSend<TransferApi> for MockApp {
    async fn handle_api_send(&self, api: PhantomData<TransferApi>, request: Self::Request)
        -> Result<Self::Response, Self::Error> {
        self.handle_api(api, request).await
    }
}
```

Each concrete forwarding impl proves `Send` for one context and API pair. This requires more impls
than a generic return-type bound would, but keeps the stronger requirement out of the abstract
interface. The built-in `CanSendRun` runner uses the same pattern through a `SendRunner` proxy on
the concrete context, allowing a spawning provider to clone the context into a `Send` future.

## Further reference

These online references describe the constructs as of CGP v0.8.0:

- [concepts/handlers.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/handlers.md)
- [concepts/dispatching.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/dispatching.md)
- [concepts/monadic-handlers.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/monadic-handlers.md)
- [concepts/send-bounds.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/send-bounds.md)
- [components/computer.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/components/computer.md)
- [components/try_computer.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/components/try_computer.md)
- [components/handler.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/components/handler.md)
- [components/producer.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/components/producer.md)
- [components/runner.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/components/runner.md)
- [macros/cgp_computer.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_computer.md)
- [macros/cgp_producer.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_producer.md)
- [macros/cgp_auto_dispatch.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_auto_dispatch.md)
- [providers/handler_combinators.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/providers/handler_combinators.md)
- [providers/dispatch_combinators.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/providers/dispatch_combinators.md)
- [providers/monad_providers.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/providers/monad_providers.md)
