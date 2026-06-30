# Skin64Beta — architecture findings

Re-verified against the fresh Skin64Beta project's actual compiled game jar
(biny mappings `b1.7.3+4cbd9c8:v2` — same as before, confirmed identical
byte-for-byte on the classes below). All class/field/method names are real,
read directly out of the mapped jar, not recalled from training data.

Scope note: this version drops everything related to supporting 64x32 skins
or detecting-which-format, since Skin64Beta is 64x64-only by design. Anything
not 64x64 falls back to vanilla (unmodified) Steve rendering — our new code
simply does not engage for non-64x64 skins.

## The model: `BipedEntityModel` (extends `EntityModel`)

Fields today: `head, hat, body, rightArm, leftArm, rightLeg, leftLeg, ears,
cape` (all `ModelPart`), plus `leftArmPose`, `rightArmPose`, `sneaking`
(booleans).

No jacket/sleeve/pants parts exist. `render(FFFFFF)` draws exactly:
`head, body, rightArm, leftArm, rightLeg, leftLeg, hat`. We have to add new
`ModelPart` fields ourselves — this is new geometry, not a hidden toggle.

The existing `hat` part is our template: it's a second `ModelPart` sharing
`head`'s pivot, with its own UV baked in at construction time, scaled
slightly outward from `head` so it draws just outside the base head cuboid.
Jacket/sleeves/pants will follow the same pattern relative to `body`/`rightArm`/
`leftArm`/`rightLeg`/`leftLeg`.

## `ModelPart` mechanics

- `addCuboid(x,y,z, sizeX,sizeY,sizeZ, u,v, scaleExpand)` bakes geometry AND
  texture UV together, at construction time, into a `Quad[]`/`Vertex[]` pair.
- First call to `render(F)` compiles the part into an OpenGL display list
  (`compiled: Z` flag). This means: any new `ModelPart` we add must have its
  UV/geometry fully set up in the model's constructor, before first render —
  not computed lazily based on runtime skin inspection. The UV is baked
  static vertex data, not a per-frame texture-coordinate transform.
- `mirror: Z` flips U-mapping for left-side parts reusing right-side UV
  regions (used by `leftArm`/`leftLeg` today).
- `visible: Z` is how the existing armor system hides body parts under
  armor — same mechanism we could use to skip drawing an overlay part if
  needed later, but not required for the first version.

## `decorationModel` is a trap — confirmed, do not use

`LivingEntityRenderer` has a `decorationModel` field that looks built for
exactly an overlay layer. It's already claimed: `PlayerEntityRenderer.bindTexture`
calls `setDecorationModel(armor1 or armor2)` based on armor slot parity —
this is the armor-layering system, not a free overlay slot. Using it for our
jacket/sleeves/pants layer would collide with armor rendering. We need our
own separate render pass.

## Render call sequence — `LivingEntityRenderer.render(LivingEntity,D,D,D,F,F)`

In order:
1. Apply riding/yaw/pitch state to `model`.
2. Translation/rotation setup, alpha test, scale, `applyScale`.
3. `bindDownloadedTexture(entity.skinUrl, entity.getTexture())` — main skin
   texture bind, for every living entity including players.
4. `model.animateModel(...)`
5. `model.render(...)` — draws base layer (head/body/arms/legs/hat).
6. `bindTexture(entity, 0, partialTick)` then `decorationModel.render(...)` —
   this is the armor pass for players (see above, not ours to touch).
7. `renderMore(entity, partialTick)` — items, cape, ears.
8. Hurt/death-tint extra passes.
9. `renderNameTag`.

**Working injection point for our second draw pass: right after step 5**
(`model.render(...)` returns), before step 6's armor bind. Inject into
`LivingEntityRenderer.render`, guarded by `entity instanceof PlayerEntity`
(so non-player mobs are untouched) and by our own "is this player's skin
64x64" check (see below). Still needs hands-on confirmation of the exact
`@At` injection point once we're writing the actual Mixin — this is the
plan, not yet proven against real Mixin tooling.

## Texture loading — where the 64x64 check has to live

Two separate skin-loading code paths exist in vanilla:

1. **Downloaded-by-URL skins** (`entity.skinUrl != null`, the old pre-UUID
   mechanism): goes through `WorldRenderer.notifyEntityAdded` →
   `TextureManager.downloadImage(url, new SkinImageProcessor())`.
   `SkinImageProcessor` does legacy 64x32 alpha-channel cleanup — irrelevant
   to us now, since we're not supporting 64x32 at all. Not touching this class.

2. **Local skin selection** (what we'll actually test against first): goes
   straight through `TextureManager.downloadTexture(skinUrl, resourcePath)`
   → falls through to `getTextureId(resourcePath)` when no URL is set →
   plain image load → straight GL texture upload. **Nothing here inspects
   image height at all today.** This is the path we need to hook to learn
   "is this image 64 tall."

Plan: hook into the local image-loading path (`TextureManager`, likely
around `getTextureId`/`readImage`/`rescale`) to capture the loaded
`BufferedImage`'s height before it's discarded, and remember it (keyed by
texture path, or by player) for our render-pass check. Exact Mixin target
method not yet chosen — this is the next concrete decision once we start
writing code, alongside the injection point above.

## Open questions, carried into active work

1. Exact `@At` target for the second draw pass in `LivingEntityRenderer.render`.
2. Exact Mixin target + storage mechanism for remembering "this skin's image
   was 64 tall" past texture upload (a side-table keyed by something stable
   — texture resource path is the leading candidate over per-player state,
   since it's simpler and skins are texture-path-identified in this version
   of the game).
3. UV layout for the new jacket/sleeve/pants `ModelPart`s — needs to match
   the standard modern second-layer skin region layout (bottom 32 rows of
   the 64x64 image). Not yet mapped out pixel-by-pixel against our reference
   skin.

## Tooling

`tools/classdump.py` — pure Python, no dependencies, reads compiled `.class`
files directly out of any jar and prints fields/methods/bytecode references,
used to produce everything above without needing a working decompiler.
Usage: `python3 classdump.py <jar-path> <internal/class/Path.class> [method-name-filter]`
