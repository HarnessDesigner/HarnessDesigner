import pynvml

pynvml.nvmlInit()

pynvml.NVML_SUCCESS
pynvml.NVML_ERROR_DRIVER_NOT_LOADED
pynvml.NVML_ERROR_NO_PERMISSION
pynvml.NVML_ERROR_UNKNOWN


pynvml.nvmlShutdown()

cudaDriverVersion: int = pynvml.nvmlSystemGetCudaDriverVersion()
cudaDriverVersion: int = pynvml.nvmlSystemGetCudaDriverVersion_v2()


nvmlSystemDriverBranchInfo: pynvml.c_nvmlSystemDriverBranchInfo_v1_t = pynvml.nvmlSystemGetDriverBranch()
nvmlSystemDriverBranchInfo.version
nvmlSystemDriverBranchInfo.branch

version: str = pynvml.nvmlSystemGetDriverVersion()



hics: list[pynvml.c_nvmlHwbcEntry_t] = pynvml.nvmlSystemGetHicVersion()
hics[index].firmwareVersion


version: str = pynvml.nvmlSystemGetNVMLVersion()
name: str = pynvml.nvmlSystemGetProcessName(pid)
nvmlDevices: list[pynvml.c_nvmlDevice_t] = pynvml.nvmlSystemGetTopologyGpuSet(cpuNumber)




nvmlDeviceArchitecture_t
nvmlDeviceAttributes_t
nvmlBAR1Memory_t
nvmlClockType_t
nvmlConfComputeMemSizeInfo_t
nvmlMemory_t
nvmlCoolerInfo_t
nvmlDeviceCurrentClockFreqs_t
nvmlEnableState_t
nvmlGpuDynamicPstatesInfo_t
nvmlMarginTemperature_t
nvmlClockType_t



nvmlDeviceGetCount_v2


nvmlDeviceGetBoardPartNumber
nvmlDeviceGetBrand
nvmlDeviceGetBridgeChipInfo
nvmlDeviceGetBusType

nvmlDeviceGetClock
nvmlDeviceGetClockInfo

nvmlDeviceGetConfComputeMemSizeInfo
nvmlDeviceGetConfComputeProtectedMemoryUsage

nvmlDeviceGetCoolerInfo

nvmlDeviceGetCurrPcieLinkWidth
nvmlDeviceGetCurrentClockFreqs


nvmlDeviceGetDisplayMode

nvmlDeviceGetDynamicPstatesInfo

nvmlDeviceGetFanSpeed
nvmlDeviceGetFanSpeedRPM
nvmlDeviceGetFanSpeed_v2



nvmlDeviceGetHandleByIndex_v2

nvmlDeviceGetMarginTemperature

nvmlDeviceGetMaxClockInfo
nvmlDeviceGetMaxCustomerBoostClock
nvmlDeviceGetMaxPcieLinkWidth
nvmlDeviceGetMemoryBusWidth

nvmlDeviceGetMemoryInfo
nvmlDeviceGetMemoryInfo_v2


nvmlDeviceGetMinMaxFanSpeed
nvmlDeviceGetMultiGpuBoard
nvmlDeviceGetName


nvmlDeviceGetNumFans
nvmlDeviceGetNumGpuCores

nvmlDeviceGetPcieLinkMaxSpeed
nvmlDeviceGetPcieSpeed
nvmlDeviceGetPcieThroughput
nvmlDeviceGetPowerUsage
nvmlDeviceGetSerial


nvmlDeviceGetTargetFanSpeed

nvmlDeviceGetTemperature
nvmlDeviceGetTemperatureThreshold
nvmlDeviceGetTemperatureV
nvmlDeviceGetThermalSettings


nvmlDeviceGetTotalEnergyConsumption

nvmlDeviceGetUtilizationRates

nvmlDeviceGetVbiosVersion



try:


    gpus = GPUtil.getGPUs()
    if gpus:
        gpu = gpus[0]
        self.total_vram = gpu.memoryTotal / 1024
        self.free_vram = gpu.memoryFree / 1024
        print(f"✓ NVIDIA VRAM via GPUtil: {self.free_vram:.1f}GB free")
        return
except:
    pass