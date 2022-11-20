// SPDX-License-Identifier: GPL-3.0-or-later
const { spawnSync } = require('child_process');
const { argv, stdout, stderr } = require('process');

spawnSync(
    'python',
    ['-m', 'ci_core_dumper', '-v', 'report'].concat(argv.slice(2)),
    {stdio: ['ignore', 'inherit', 'inherit']},
)
