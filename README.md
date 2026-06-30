# Skin64Beta

A Mixin-only client mod for vanilla Minecraft Beta 1.7.3 that teaches the
game to natively render modern 64x64 double-layer player skins.

## The problem

Beta 1.7.3 only understands flat 64x32 skins — one layer, no overlay. Modern
skins are 64x64: the bottom half holds a second layer (jacket, sleeves, pant
legs) meant to render slightly outside the base body. b1.7.3 doesn't reject
a 64x64 file, it just never looks at the bottom half — that data sits there
unused, and the in-game player model has no geometry to display it with even
if it tried.

## What this mod does

* Recognizes 64x64 skins and renders their second layer as real 3D geometry
(new model parts for jacket, sleeves, and pant legs, layered just outside
the base body — the same technique vanilla already uses for the hat layer
on the head).
* **64x64 only.** If a skin isn't 64x64, this mod doesn't try to partially
support it — it falls back entirely to vanilla behavior (Steve, 64x32).
No format-detection branching, no compatibility shimming. One shape in,
one shape rendered correctly.

## What this mod does *not* do

* It does not let you assign a custom skin to a player without a proxy.
Vanilla b1.7.3 only natively recognizes one skin (Steve). Getting your own
custom texture onto a player at all, in this version of the game, has
always required a proxy. Skin64Beta doesn't change that — it only changes
what happens once a 64x64 texture *is* in front of the renderer, however
it got there. (Removing the proxy requirement is a separate mod — see
below.)
* It does not render the second layer with real depth/offset in 3D space.
This mod adds the geometry and gets it positioned correctly relative to
the base body, following the same pattern vanilla already uses for hats.
Full 3D layering effects are a separate, later mod.

## Part of a three-mod arc

This is the first of three related mods, each building on the last:

1. **Skin64Beta** (this mod) — teaches the renderer to understand 64x64
skins as real geometry.
2. **Beta64Native** (planned) — removes the proxy requirement for assigning
custom skins to players natively, for quality of life.
3. **BetaSkin3D** (planned) — full 3D depth/offset rendering for the second
layer, building on the geometry this mod establishes.

## Why beta 1.7.3, specifically

This is intentional, sustained focus on one version of the game rather than
spreading effort thin across many. The goal is deep, durable expertise in
b1.7.3's internals specifically.

## Toolchain

* Upstream `fabric-loom` + `babric-loom-extension`
* `biny` mappings via `net.glasslauncher:biny`
* Java 17, Kotlin DSL build files

Mappings and loader versions in this ecosystem move fast and aren't
strongly pinned upstream — don't assume a version string or repo URL from
outside this project's own `build.gradle.kts`/`gradle.properties` is still
correct without checking those files first.

## Project structure

```
Skin64Beta/
├── src/main/             vanilla mod source (Mixins, mod entrypoint)
├── notes/                architecture research notes (see notes/architecture-findings.md)
├── tools/                helper scripts used during development (see tools/)
├── lucyskin/              reference 64x64 test skin
└── build.gradle.kts      build config — source of truth for toolchain versions
```

## Status

Early development. Scaffold builds and runs. Architecture has been mapped
out by reading the actual decompiled-equivalent game code (see
`notes/architecture-findings.md`); no feature code written yet.

