# Reference Canonical Skeletal Framework

Copyright 2025 Nick Porcino

## Purpose

Humanoid skeletons are named and structured differently by nearly every tool that uses them, which makes moving characters and animation between content creation, game, and virtual-world pipelines harder than it should be.

The Reference Canonical Skeletal Framework (RCSF) surveys the major skeletal formats and defines a canonical set of joints that each format maps onto. The aim is a clear, well-documented pivot for translating between formats — not a new universal skeleton that everyone is expected to adopt. Format-specific choices are preserved; RCSF just provides the common reference in the middle.

## Contents

- `survey.md` - Per-format analysis of the surveyed skeletal standards (OpenUSD, VRM, HAnim, SMPL-X, BVH, ASF/AMC, Mixamo, UE Mannequin, Unity Mecanim, and others)
- `joints.csv` - The mapping table: each canonical joint alongside its equivalent in every surveyed format
- `proposal.md` - Draft proposal for the Metaverse Standards Forum
- `references.md` - Primary information sources for each of the studied formats
- `README.md` - This overview document
- `skels/` - The mapping table exploded into one human-editable TOML file per skeleton, plus `_canonical.toml` (the pivot defining joint and column order). This is the source you edit; `joints.csv` is regenerated from it. See [Editing the Mapping](#editing-the-mapping).
- `split_csv.py`, `join_csv.py`, `rcsf.py` - Small dependency-free tools that explode `joints.csv` into `skels/` and stitch it back, verifying the round-trip is lossless.

## Editing the Mapping

`joints.csv` is a wide table (one row per canonical joint, one column per
skeleton), which grows unwieldy to review in a pull request. To keep edits
small and reviewable, the table is kept exploded under `skels/`:

```
skels/
  _canonical.toml     # the pivot: canonical joint order + column order (edit to add rows/columns)
  OpenUSD.toml        # one file per skeleton: canonical joint -> that format's joint name
  VRM.toml            # ("-" means the format has no equivalent for that joint)
  ...                 #
  ANNY.toml           #
```

**`skels/` is the source of truth; `joints.csv` is a generated artifact.** You
edit the small TOML files, then regenerate the CSV. The tooling is pure Python
3.11+ (stdlib only — no `pip install`), and every regeneration verifies the
round-trip is byte-exact, so nothing is ever silently lost.

Two commands cover everything:

```bash
python3 join_csv.py            # CHECK: does skels/ still reproduce joints.csv? (exits non-zero on drift)
python3 join_csv.py --write    # APPLY: regenerate joints.csv from skels/, printing every changed cell
```

The `--write` change summary is the safety net: it lists exactly which cells
moved (e.g. `[HAnim] LeftHand: 'hand_l' -> 'l_radiocarpal'`), so an accidental
off-by-one or wrong-column edit is obvious before you commit.

### Common tasks

- **Fix or refresh one skeleton's joint names**
  Edit its `skels/<Skeleton>.toml`, then `python3 join_csv.py --write` and review the printed diff. Commit the `.toml` and the regenerated `joints.csv` together.

- **Add a new skeleton (a new column)**
  1. Create `skels/<Name>.toml` with a `skeleton = "<Name>"` line and a `[values]` table mapping **every** canonical joint to that format's name (`"-"` where none).
  2. Append `"<Name>"` to the `skeletons` list in `skels/_canonical.toml` (its position sets the column order).
  3. `python3 join_csv.py --write`.

- **Add a new canonical joint (a new row)**
  1. Insert the joint name into the `joints` list in `skels/_canonical.toml` at the correct hierarchy position (this sets row order).
  2. Add that same key to the `[values]` table of **every** `skels/*.toml`.
  3. `python3 join_csv.py --write`. (`join_csv.py` errors clearly if any skeleton file is missing the new joint, so you can't half-add a row.)

- **Rebuild `skels/` from scratch** (e.g. after editing `joints.csv` directly)
  `python3 split_csv.py` re-explodes the CSV into `skels/`; follow with `python3 join_csv.py` to confirm they agree.

Because each skeleton lives in its own file, a PR that touches one format shows
a clean, self-contained diff — and `python3 join_csv.py` in CI will fail if
`joints.csv` and `skels/` ever fall out of sync.

## Tasks

### Validate each of the format descriptions:

- [ ] OpenUSD - Pixar Universal Scene Description skeletal framework
- [x] VRM - VRoid [humanoid avatar specification](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/humanoid.md)
- [x] HAnim - Web3D Consortium humanoid animation standard
- [ ] SMPL-X - Statistical Multi-Person Linear model eXpressive
- [ ] BVH - Biovision Hierarchy motion capture format
- [ ] ASF/AMC - Acclaim motion capture format
- [ ] Mixamo - Adobe automated animation service
- [ ] UE Mannequin - Unreal Engine reference skeleton
- [x] Unity Mecanim - Unity semantic humanoid system
- [x] Godot - Godot Engine [SkeletonProfileHumanoid](https://docs.godotengine.org/en/stable/classes/class_skeletonprofilehumanoid.html)
- [ ] Second Life - Linden Lab Bento and legacy skeletons
- [ ] Roblox - R15 Reference Skeleton
- [ ] Momentum Humanoid Rig - Meta SAM3D Body Skeleton
- [x] ANNY - NAVER Labs [differentiable parametric body model](https://github.com/naver/anny) (MakeHuman-derived "anny" rig)

### Create Tools

- [ ] CSV-to-mapping-algorithm converter
- [ ] Joint hierarchy validation tool
- [ ] Cross-format conversion engine
- [ ] Anatomical consistency validator
- [ ] Animation quality assessment framework
- [ ] Performance benchmarking suite
- [ ] Community validation platform
- [ ] Reference implementation library

### Research Documentation

- [x] Locate primary SMPL-X academic publications and implementation repositories
- [x] Find original BVH format specifications and comprehensive documentation
- [x] Locate CMU ASF/AMC format documentation and motion capture database references
- [x] Find Adobe Mixamo technical documentation and API specifications
- [x] Locate Epic Games UE Mannequin skeletal system documentation
- [x] Find Unity Mecanim Humanoid Animation system technical documentation
- [x] Verify and update all reference links for accuracy and completeness

## RFC

### Technical

- [x] How should twist bones be handled in minimal target formats?
  - **Resolved**: incorporate description into the main text.
  - Diagrams would be good to incorporate.
  - A twist joint (sometimes called a roll or twist bone) is a helper joint inserted along a limb — usually the upper arm, forearm, thigh, or calf — to distribute rotational deformation (especially twisting around the bone’s primary axis) more naturally across the mesh. ${Twist}_{Rotation} = {Parent}_{Rotation} * {Twist}_{Weight}$
- [x] Should facial expression joints use standardized blendshape names?
  - **Resolved**: In future development, we could provide guidance on how the face joints (which are pseudo-skin/muscle clusters) that they map in some manner to FACS. Specifying FACS is out of scope, but referencing it canonically is in scope.
    Facial expressions in general are going to be a combination of joints and blendshapes.
    Breaking out expressions as a future topic seems like a strong direction.
- [ ] What constitutes acceptable quality loss during downward conversion?
- [ ] What validation metrics best assess cross-format conversion quality?
- [x] Should there be performance tiers for different hardware capabilities?
  - **Resolved**: An avatar can use a cluster geometry for hierarchy (like a suit of armor), or it can be skin-cluster weighted.
  - We can describe common techniques as informative text.
  - Skeletal LODs define subsets of bones.
  - The hierarchy definition can show how Skeletal subsets map to the canonical hierarchy. We could provide guidance as to common methods for delegating functionality to articulation schemes within the same hierarchy.

### Compatiblity

- [ ] How do we handle proprietary engine-specific features (Animation Blueprints, etc.)?
- [ ] How should the framework accommodate emerging standards (VR haptics, AI-driven animation)?

## License

Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)

This work is licensed under the Creative Commons Attribution-ShareAlike 4.0 International License. You are free to share and adapt this material for any purpose, even commercially, under the following terms:

- **Attribution** - You must give appropriate credit and indicate if changes were made
- **ShareAlike** - If you remix, transform, or build upon the material, you must distribute your contributions under the same license

This license promotes collaborative development while ensuring that improvements benefit the broader community working on humanoid skeletal interoperability challenges.
