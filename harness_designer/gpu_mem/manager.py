class GPUMemoryManager:
    """Smart VRAM detection based on OpenGL vendor info"""

    def __init__(self, vendor, opencl_device=None):
        self.device = opencl_device
        self.vendor = vendor

        self.total_vram = None
        self.free_vram = None
        self._detect()

    def _detect(self):
        """Detect GPU vendor via OpenGL, then use appropriate method"""

        # Get vendor from OpenGL
        try:
            vendor_str = glGetString(GL_VENDOR).decode('utf-8').lower()
            renderer = glGetString(GL_RENDERER).decode('utf-8')

            if 'nvidia' in vendor_str:
                self.vendor = 'NVIDIA'
                self._detect_nvidia()
            elif 'amd' in vendor_str or 'ati' in vendor_str:
                self.vendor = 'AMD'
                self._detect_amd()
            elif 'intel' in vendor_str:
                self.vendor = 'Intel'
                self._detect_intel()
            elif 'apple' in vendor_str or 'metal' in renderer.lower():
                self.vendor = 'Apple'
                self._detect_apple()
            else:
                self.vendor = 'Unknown'
                self._detect_fallback()

            print(f"Detected GPU: {self.vendor} - {renderer}")
            print(f"Available VRAM: {self.free_vram:.1f} GB")

        except Exception as e:
            print(f"OpenGL detection failed: {e}")
            self._detect_fallback()

    def _detect_nvidia(self):
        """NVIDIA-specific detection"""


        # Fallback to OpenCL estimate
        self._detect_opencl_estimate(multiplier=0.6)

    def _detect_amd(self):
        """AMD-specific detection"""
        try:
            import pyamdgpuinfo

            gpu = pyamdgpuinfo.get_gpu(0)
            self.total_vram = gpu.memory_info['vram_size'] / (1024 ** 3)
            self.free_vram = (gpu.memory_info['vram_size'] -
                              gpu.memory_info['vram_used']) / (1024 ** 3)
            print(f"✓ AMD VRAM via pyamdgpuinfo: {self.free_vram:.1f}GB free")
            return
        except:
            pass

        # Fallback to OpenCL estimate
        self._detect_opencl_estimate(multiplier=0.5)

    def _detect_intel(self):
        """Intel integrated graphics (shared memory)"""
        # Intel typically shares system RAM, be conservative
        self._detect_opencl_estimate(multiplier=0.3)
        print(f"⚠ Intel GPU uses shared memory, being conservative")

    def _detect_apple(self):
        """Apple Silicon unified memory"""
        # Apple Silicon shares memory with CPU, be conservative
        self._detect_opencl_estimate(multiplier=0.4)
        print(f"⚠ Apple GPU uses unified memory, being conservative")

    def _detect_opencl_estimate(self, multiplier=0.6):
        """Estimate available VRAM from OpenCL total memory"""
        try:
            if self.device:
                total = self.device.global_mem_size / (1024 ** 3)
                self.total_vram = total
                self.free_vram = total * multiplier
                print(
                    f"⚠ Estimated VRAM: {self.free_vram:.1f}GB ({int(multiplier * 100)}% of {total:.1f}GB)"
                    )
                return
        except:
            pass

        self._detect_fallback()

    def _detect_fallback(self):
        """Ultra-conservative fallback"""
        self.total_vram = 4.0
        self.free_vram = 2.0
        print(f"⚠ Using fallback: {self.free_vram:.1f}GB (conservative)")

    def get_optimal_chunk_size(self, width, height, target_usage=0.4):
        """
        Calculate optimal chunk size based on available VRAM

        Args:
            width: Image width
            height: Image height
            target_usage: Fraction of free VRAM to use per chunk (0.0-1.0)

        Returns:
            Optimal chunk size in rows
        """
        target_vram_gb = self.free_vram * target_usage
        bytes_per_pixel = 3 * 4  # RGB float32
        target_pixels = (target_vram_gb * 1024 ** 3) / bytes_per_pixel
        chunk_size = int(target_pixels / width)

        # Ensure reasonable bounds
        chunk_size = max(50, min(chunk_size, height))

        num_chunks = (height + chunk_size - 1) // chunk_size
        vram_per_chunk = (width * chunk_size * bytes_per_pixel) / (1024 ** 3)

        print(f"\nChunk strategy for {width}x{height}:")
        print(f"  Chunk size: {chunk_size} rows")
        print(f"  Num chunks: {num_chunks}")
        print(f"  VRAM/chunk: {vram_per_chunk:.2f}GB")
        print(f"  Est. GPU usage: {'100%' if num_chunks > 1 else '~90%'}")

        return chunk_size

    def recommend_strategy(self, width, height):
        """Recommend rendering strategy"""
        total_pixels = width * height
        needed_vram = (total_pixels * 3 * 4) / (1024 ** 3)

        if needed_vram < self.free_vram * 0.8:
            # Can render in one go
            return {
                'strategy': 'single_pass',
                'chunk_size': height,
                'expected_time_multiplier': 1.0,
                'gpu_usage': '85-95%',
                'reason': f'Image fits in VRAM ({needed_vram:.1f}GB < {self.free_vram * 0.8:.1f}GB)'
            }
        else:
            # Need chunking
            optimal_chunks = max(2, int(needed_vram / (self.free_vram * 0.4)))
            return {
                'strategy': 'chunked',
                'chunk_size': height // optimal_chunks,
                'expected_time_multiplier': 1.5,
                'gpu_usage': '95-100%',
                'reason': f'Image too large ({needed_vram:.1f}GB), using {optimal_chunks} chunks'
            }