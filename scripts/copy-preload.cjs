const fs = require("node:fs");
fs.copyFileSync("electron/preload.cjs", "dist-electron/electron/preload.cjs");
fs.copyFileSync('shared/core-events.sql', 'dist-electron/shared/core-events.sql');
fs.copyFileSync('shared/music-schema.sql', 'dist-electron/shared/music-schema.sql');
