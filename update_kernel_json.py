import os
import json
# updates the JUPYTER_CONFIG_DIR of the IAM kernel.json, so we use our custom config jupyter notebook files and do not mess with students local config
cwd = os.getcwd()
kernel_json_path = "/home/.local/share/jupyter/kernels/iam_kernel/kernel.json"
with open(kernel_json_path, 'r') as f:
    kernel_json = json.load(f)
jupyter_config_dir_env = {"JUPYTER_CONFIG_DIR":f"{cwd}/jupyter_config/"}
if "env" in kernel_json.keys():
    print(f"Found 'env' in kernel.json and updating it with {jupyter_config_dir_env}")
    kernel_json["env"].update(jupyter_config_dir_env)
else:
    kernel_json["env"] = jupyter_config_dir_env
    print(f"Did not find 'env' in kernel.json and creating it with {jupyter_config_dir_env}")
with open(kernel_json_path, 'w') as f:
    json.dump(kernel_json, f, indent=2)