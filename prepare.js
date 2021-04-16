const { spawnSync } = require('child_process');
const { argv, stdout, stderr } = require('process');
const os = require('os');

console.log(argv[1]);

if(os.type()=='Linux') {
    console.log('::group::Install GDB')

    spawnSync(
        'sudo',
        ['apt-get', 'update'],
        {stdio: ['ignore', 'inherit', 'inherit']},
    )

    spawnSync(
        'sudo',
        ['apt-get', '--yes', '--no-install-recommends', 'install', 'gdb'],
        {stdio: ['ignore', 'inherit', 'inherit']},
    )
    console.log("::endgroup::")
}

const fs = require('fs');
const path = require('path');
const process = require('process');

// we are called like:
//   nodejs /path/to/analyze.js
const actiondir = path.dirname(argv[1]);

// modify PYTHONPATH for our child process
process.env.PYTHONPATH = actiondir+path.delimiter+(process.env.PYTHONPATH||'')

// modify PYTHONPATH for post and intermediate
// cf. https://docs.github.com/en/free-pro-team@latest/actions/reference/workflow-commands-for-github-actions#setting-an-environment-variable
fs.appendFileSync(
    process.env.GITHUB_ENV,
    'PYTHONPATH='+process.env.PYTHONPATH,
);

if(os.type()=='Windows_NT') {
    console.log('Adjust PATH')
    // add our dummy 'ulimit' command to %PATH%
    // cf. https://docs.github.com/en/free-pro-team@latest/actions/reference/workflow-commands-for-github-actions#adding-a-system-path
    fs.appendFileSync(
        process.env.GITHUB_PATH,
        actiondir,
    );
}

console.log('::group::ci-core-dumper install')
spawnSync(
    'python',
    ['-m', 'ci_core_dumper', '-v', 'install'].concat(argv.slice(2)),
    {stdio: ['ignore', 'inherit', 'inherit']},
)
console.log("::endgroup::")
