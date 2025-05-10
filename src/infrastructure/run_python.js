const {spawnSync} = require("child_process")
const os = require('os');

const script = process.argv[2];
const script_args = process.argv.slice(3)
switch (os.platform())
{
    case "win32":
        spawnSync("venv\\Scripts\\python",[`${script} ${script_args.join(" ")}`], 
            {stdio:"inherit", shell: true});
        break;
    case "linux":
        spawnSync("venv/bin/python",[`${script} ${script_args.join(" ")}`], 
            {stdio:"inherit", shell: true});
        break;
    default:
        console.error("Failed to use Python, OS not supported")
        break;
}