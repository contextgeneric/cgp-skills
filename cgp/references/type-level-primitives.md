# Type-level primitives

CGP encodes field names, positions, lists, and wiring paths as types so the compiler can resolve
them through traits. Use the macros when writing these types, and recognize their expanded forms
when reading diagnostics. This reference describes CGP v0.8.0.

## The idea

Type-level encodings let trait resolution distinguish keys that would otherwise be values. A getter
uses a field tag, a [wiring](wiring.md) table uses a [component](components.md) marker, and a
[namespace](namespaces.md) uses a path. Strings become character-list types, positions become
const-generic markers, and lists become recursive types.

Prefer `Symbol!`, `Product!`, `Sum!`, and `Path!` to their nested expansions. Derives also generate
these encodings. Compiler errors and plain `cargo expand` can expose the full types;
`cargo cgp expand` restores recognized encodings to macro notation. The definitions below explain
the nested forms that remain visible.

Assume `use cgp::prelude::*;` throughout.

## Type-level lists: `Product!`, `Cons`, `Nil`

`Product!` represents a list as nested pairs ending in `Nil`. Each `Cons<Head, Tail>` holds an
element and the rest of the list, allowing generic code to process an anonymous product type one
element at a time:

```rust
pub struct Cons<Head, Tail>(pub Head, pub Tail);
pub struct Nil;
```

Use `Product!` to construct the type and lowercase `product!` to construct a value. Both expand to
the same nested `Cons` structure:

```rust
type Row = Product![u32, String, bool];
// Row == Cons<u32, Cons<String, Cons<bool, Nil>>>

let row: Row = product![1, "hi".to_string(), true];
// row == Cons(1, Cons("hi".to_string(), Cons(true, Nil)))
```

Product lists let generic providers process struct fields without naming the concrete struct.
`HasFields` exposes a struct's fields as a product, usually containing
[`Field`](#field-a-named-value) entries that pair names with values. A recursive provider handles
`Nil` as its base case and `Cons<Head, Tail>` as its step. See [extensible data](extensible-data.md)
for reading and rebuilding records this way.

## Type-level sums: `Sum!`, `Either`, `Void`

`Sum!` holds a value from one branch, while `Product!` holds a value for every element. It nests
`Either<Head, Tail>` enums and terminates in the uninhabited `Void` type:

```rust
pub enum Either<Head, Tail> { Left(Head), Right(Tail) }
pub enum Void {}
```

`Left(head)` selects the current branch, and `Right(tail)` continues into the remaining branches.
`Sum!` constructs this nested type, so the number of `Right` wrappers identifies a value's branch:

```rust
type Token = Sum![u32, String, bool];
// Token == Either<u32, Either<String, Either<bool, Void>>>

let t: Token = Either::Right(Either::Left("hi".to_string())); // the String branch
```

`Void` makes exhausted variant handling statically complete. Once an extractor has handled every
branch, the remaining type is an empty enum, which can be eliminated with `match self {}`. A product
instead ends in constructible `Nil` because an empty record is a valid value.

`HasFields` exposes an enum's variants as a `Sum!` of `Field` entries. This parallels a struct's
`Product!` representation while retaining the distinction between choosing one variant and holding
all fields.

## Type-level strings: `Symbol!`, `Symbol`, `Chars`

`Symbol!("name")` turns a field name into a type suitable for a `HasField<Tag>` key. Equal string
literals produce the same type, and different strings produce different types, so trait resolution
can distinguish field names.

CGP stores symbols as character lists because stable Rust cannot use `&str` as a const-generic
parameter. Individual `char` parameters are supported, so `Chars` stores each character and `Symbol`
wraps the list with its UTF-8 byte length:

```rust
pub struct Chars<const CHAR: char, Tail>(pub PhantomData<Tail>);
pub struct Symbol<const LEN: usize, Chars>(pub PhantomData<Chars>);
```

`Symbol!` computes the byte length and generates the nested character list. The explicit length lets
the runtime string-recovery machinery size its byte array without computing that size from the list
in a const-generic expression:

```rust
// before
Symbol!("abc")
// after
Symbol<3, Chars<'a', Chars<'b', Chars<'c', Nil>>>>
```

The length counts UTF-8 bytes, while the list has one node per Unicode scalar value.
`Symbol!("世界你好")` therefore has length `12` and four character nodes. The empty string is
`Symbol<0, Nil>`.

A `HasField` bound uses the symbol to identify the field a provider needs. This explicit form shows
the tag lookup that an implicit field argument normally hides:

```rust
#[cgp_impl(new GreetHello)]
impl Greeter
where
    Self: HasField<Symbol!("name"), Value = String>,
{
    fn greet(&self) {
        println!("Hello, {}!", self.get_field(PhantomData::<Symbol!("name")>));
    }
}
```

Formatting and recovery traits turn the symbol back into runtime text. See
[`StaticFormat`](#staticformat-recovering-strings-and-paths) below.

## `Index<N>`: type-level numbers

`Index<N>` identifies a tuple field by position. It serves the same role as `Symbol!("name")` for
named fields: `Index<0>`, `Index<1>`, and `Index<2>` are distinct tag types corresponding to `.0`,
`.1`, and `.2`.

```rust
pub struct Index<const I: usize>;
```

`Index` stores its number only in the type and occupies zero bytes. A tuple struct can implement
`HasField<Index<0>>` and `HasField<Index<1>>` separately. A lookup without a matching impl fails at
compile time, such as `Index<5>` on a derived three-field struct. Its `Display` impl prints the
number, so `Index::<2>.to_string()` returns `"2"`.

## `Field`: a named value

`Field<Tag, Value>` pairs a value with its type-level name. A bare `Product![String, u8]` records
types and order; `Field<Symbol!("name"), String>` also identifies the string as the `name` field.
Providers can use that tag to select fields:

```rust
pub struct Field<Tag, Value> {
    pub value: Value,
    pub phantom: PhantomData<Tag>,
}
```

The phantom tag adds neither stored data nor size to `Field`. Its size equals that of `Value`, and
its target type determines the tag when constructing it:
`let f: Field<Symbol!("name"), String> = "Alice".to_string().into();`.

`Field` represents both record fields and enum payloads. Record tags use `Symbol!` or `Index`, and
variant tags use `Symbol!`. For this struct, `HasFields` generates a product containing the named
fields:

```rust
#[derive(HasFields)]
pub struct Person { pub name: String, pub age: u8 }

// generated:
// type Fields = Product![
//     Field<Symbol!("name"), String>,
//     Field<Symbol!("age"), u8>,
// ];
```

## `Path!` and `PathCons`: type-level routes

`Path!` identifies a lookup destination through a sequence of type-level segments.
[Namespaces](namespaces.md) and redirected [wiring](wiring.md) use these paths to address providers
under prefixes. Each `PathCons<Head, Tail>` stores phantom markers for a segment and the remaining
path, ending in `Nil`. Its parameters accept `?Sized` types because the path does not store their
values:

```rust
pub struct PathCons<Head: ?Sized, Tail: ?Sized>(pub PhantomData<Head>, pub PhantomData<Tail>);
```

`Path!` builds a path from dotted segments following `@`. A single lowercase identifier becomes a
`Symbol!` unless it names a primitive type; a capitalized name remains the type it names:

```rust
type ErrorRoute = Path!(@app.error.ErrorRaiserComponent);
// PathCons<Symbol!("app"),
//     PathCons<Symbol!("error"),
//         PathCons<ErrorRaiserComponent, Nil>>>
```

The consulting table determines which provider a path resolves to. `RedirectLookup` takes both the
table and path, so the same address can resolve differently in different contexts. Namespace entries
accept the same `@` syntax without an explicit `Path!` call. See [namespaces](namespaces.md) for the
lookup mechanism.

## `Life<'a>`: a lifetime as a type

`Life<'a>` represents a lifetime where CGP's wiring machinery requires a type. `IsProviderFor`
records a component's generic parameters in a type argument, which cannot contain a bare lifetime.
The macros encode a lifetime parameter as `Life<'a>`, producing a parameter tuple such as
`(Life<'a>, T)`:

```rust
pub struct Life<'a>(pub PhantomData<*mut &'a ()>);
```

The `*mut` phantom makes `Life<'a>` invariant in `'a`: a mutable raw pointer is invariant in its
pointee type, which contains the lifetime. This preserves the lifetime as an exact parameter of the
dependency marker. The macros insert `Life` automatically, so it usually appears only in generated
`IsProviderFor` bounds.

## `MRef<'a, T>`: owned-or-borrowed

`MRef<'a, T>` lets a getter return either a borrowed or owned value. It is an ordinary runtime enum,
included here because field-access macros recognize it as a return mode:

```rust
pub enum MRef<'a, T> { Ref(&'a T), Owned(T) }
```

A getter can return `MRef::Ref` for a stored value or `MRef::Owned` for a computed one. Callers
access either through `Deref<Target = T>` or `AsRef<T>`. The `From<&'a T>` and `From<T>` impls
construct the variants; `get_or_clone` returns an owned value, cloning only the borrowed variant
when `T: Clone`:

```rust
let stored = String::from("hello");
let borrowed: MRef<'_, String> = MRef::from(&stored);
let made: MRef<'_, String>     = MRef::from(String::from("world"));
assert_eq!(&*borrowed, "hello");
let owned: String = borrowed.get_or_clone();              // clones the borrowed case
```

Field macros recognize `MRef` alongside return modes such as `&T`, `Option<&T>`, and `&str`. See
[functions and getters](functions-and-getters.md). Its lifetime constrains an ordinary borrow and
does not use the `Life<'a>` encoding.

## `StaticFormat`: recovering strings and paths

Use `Display` to format a symbol value, `StaticString::VALUE` to recover a constant string, and
`StaticFormat` to format a type without a value. These traits and the path utility use different
imports:

| Name | Import |
| --- | --- |
| `StaticFormat` | `cgp::core::base::traits` |
| `StaticString` | `cgp::core::field::traits` |
| `ConcatPath` | `cgp::prelude::*` |

The underlying `Chars`, `Cons`, `Nil`, `PathCons`, and `Symbol` types are also available through
`cgp::core::base::types`.

`StaticFormat` writes characters into a formatter and supports the `Display` impls on `Symbol` and
`Chars`. A symbol value can therefore use ordinary string formatting:

```rust
let s = <Symbol!("hello")>::default();
assert_eq!(s.to_string(), "hello");
```

`StaticString::VALUE` recovers a symbol as a compile-time `&'static str`. Its implementation
UTF-8-encodes the character list into a `[u8; LEN]`, then validates the bytes as a string. This is
why `Symbol` records its byte length. Both recovery forms preserve multibyte Unicode:

```rust
use cgp::core::field::traits::StaticString;
assert_eq!(<Symbol!("世界你好") as StaticString>::VALUE, "世界你好");
```

`ConcatPath` joins two type-level paths. It retains the first path's segments and replaces its
terminating `Nil` with the second path:

```rust
type Joined = <Path!(@a.b) as ConcatPath<Path!(@c.d)>>::Output; // the path @a.b.c.d
```

## Further reference

Consult these knowledge-base references for the complete definitions:

- [Types](https://github.com/contextgeneric/cgp-knowledge-base/tree/main/cgp/reference/types): `Cons`, `Either`, `Chars`, `Index`, `Field`, `Life`, `MRef`, and `PathCons`.
- [`Symbol!`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/symbol.md): String encoding.
- [`Product!`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/product.md) and [`Sum!`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/sum.md): Product and sum construction.
- [`Path!`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/path.md): Path construction.
- [`StaticFormat`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/traits/static_format.md): Formatting type-level strings.
