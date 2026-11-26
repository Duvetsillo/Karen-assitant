# Karen Home Glass — Home Assistant

The user replaced the light direction with a homogeneous Apple Home inspired,
dark glass interface and one natural background. This brief overrides the
previous Karen Calm light palette; the stored theme key remains Karen Calm for
compatibility with existing views and profile preferences.

Palette: night #111B20, glass rgba(25,36,41,.78), text #F3F5F5, secondary #C3CBCE,
hairline rgba(255,255,255,.14), active accessory amber #EFBD70. System typography:
-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif. Titles 30–36 px, section
headings 21 px, accessory labels 15 px, secondary state 13–14 px.

One misty forest/lake wallpaper across routes. The generated design reference
is docs/design/ha-homekit-dark-reference.png; the production wallpaper is
karen-home-forest.png. The reference is illustrative, never a live HA receipt.
No new model, credentials, entity controls, or dependencies are introduced.

All primary cards share 22 px corners, a thin inner reflection, charcoal glass,
18 px card blur and quiet depth; navigation and compact shortcuts use 12 px on mobile. Native accessory tiles use a
vertical, left-aligned layout while preserving HA handlers, icons and keyboard
semantics. Active state comes from HA, never decorative simulation. Mobile
accessory and navigation groups use two columns. Larger media/chat content
keeps one column. Blur has an opaque fallback; press feedback respects reduced
motion. No perpetual animation or magnetic effects: native Home behavior wins.

Navigation, readings, shortcuts, chat, locations and media use the same material.
The legacy detail groups preserve controls and load on demand. Natural imagery
belongs to the shared background, never arbitrary repeated device photographs.
