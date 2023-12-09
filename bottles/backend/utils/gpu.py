# gpu.py
#
# Copyright 2022 brombinmirko <send@mirko.pm>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import subprocess

from enum import Enum
from functools import lru_cache

from bottles.backend.utils.nvidia import get_nvidia_dll_path
from bottles.backend.utils.vulkan import VulkanUtils
from bottles.backend.logger import Logger

logging = Logger()


class GPUVendors(Enum):
    AMD = "amd"
    NVIDIA = "nvidia"
    INTEL = "intel"

# noinspection PyTypeChecker
class GPUUtils:
    __vendors = {
        "nvidia": "NVIDIA Corporation",
        "amd": "Advanced Micro Devices, Inc.",
        "intel": "Intel Corporation"
    }

    def __init__(self):
        self.vk = VulkanUtils()

    @staticmethod
    def is_nouveau():
        _proc = subprocess.Popen(
            "lsmod | grep nouveau",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        stdout, stderr = _proc.communicate()
        if len(stdout) > 0:
            logging.warning("Nouveau driver detected, this may cause issues")
            return True
        return False

    def get_gpu(self):
        def extract_vendor(gpu_string):
            lower_gpu_string = gpu_string.lower()
            if "nvidia" in lower_gpu_string:
                return "nvidia"
            elif "amd" in lower_gpu_string:
                return "amd"
            elif "intel" in lower_gpu_string:
                return "intel"
            else:
                return "unknown"
        
        gpus = {
            "nvidia": {
                "name": "",
                "vendor": "nvidia",
                "envs": {
                    "__NV_PRIME_RENDER_OFFLOAD": "1",
                    "__GLX_VENDOR_LIBRARY_NAME": "nvidia",
                    "__VK_LAYER_NV_optimus": "NVIDIA_only"
                },
                "icd": self.vk.get_vk_icd("nvidia", as_string=True),
                "nvngx_path": get_nvidia_dll_path()
            },
            "amd": {
                "name": "",
                "vendor": "amd",
                "envs": {
                    "DRI_PRIME": "1"
                },
                # QUESTION: which order do we want to check these?
                "icd": self.vk.get_vk_icd("amdradv", as_string=True) or self.vk.get_vk_icd("amdvlkpro", as_string=True) or self.vk.get_vk_icd("amdvlk", as_string=True)
            },
            "intel": {
                "name": "",
                "vendor": "intel",
                "envs": {
                    "DRI_PRIME": "1"
                },
                "icd": self.vk.get_vk_icd("intel", as_string=True)
            },
            "unknown": {
                "name": "unknown",
                "vendor": "unknown",
                "envs": {
                },
                "icd": self.vk.get_vk_icd("unknown", as_string=True)
            }
        }
        result = {
            # NOTE: vendors should be a list. if there are multiple gpu by same vendor, they will overwrite each other.
            "vendors": {},
            "prime": {
                "integrated": None,
                "discrete": None
            }
        }

        if self.is_nouveau():
            gpus["nvidia"]["envs"] = {"DRI_PRIME": "1"}
            gpus["nvidia"]["icd"] = ""

        gpu_name = self.vk.get_vulkan_gpu_name(False)
        prime_gpu_name = self.vk.get_vulkan_gpu_name(True)
        gpu_vendor = extract_vendor(gpu_name)
        prime_gpu_vendor = extract_vendor(prime_gpu_name)
        gpu = gpus[gpu_vendor]
        gpu["name"] = gpu_name
        # TODO: what about same vendor integrated/discrete? they would overwrite each other.
        if prime_gpu_name and prime_gpu_vendor != gpu_vendor:
            prime_gpu = gpus[prime_gpu_vendor]
            prime_gpu["name"] = prime_gpu_name
            result["vendors"] = prime_gpu
            result["prime"]["discrete"] = prime_gpu
            result["prime"]["integrated"] = gpu
        result["vendors"] = gpu

        return result

    @staticmethod
    @lru_cache
    def is_gpu(vendor: GPUVendors) -> bool:
        _proc = subprocess.Popen(
            f"lspci | grep -iP '{vendor.value}'",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        stdout, stderr = _proc.communicate()
        return len(stdout) > 0
