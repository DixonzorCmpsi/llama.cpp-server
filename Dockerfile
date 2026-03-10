# ==============================================================================
# ON-PREM AI SERVER: LLAMA.CPP (NVIDIA CUDA + DYNAMIC CPU FALLBACK)
# ==============================================================================

# ------------------------------------------------------------------------------
# STAGE 1: Builder
# We must use the heavy NVIDIA development image to access the nvcc compiler.
# ------------------------------------------------------------------------------
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN git clone https://github.com/ggml-org/llama.cpp.git .

# Compile with Dynamic Backends (GGML_BACKEND_DL=ON). 
# This builds the core server, plus ggml-cuda.so and ggml-cpu.so separately.
RUN cmake -B build \
    -DGGML_NATIVE=OFF \
    -DGGML_CUDA=ON \
    -DGGML_BACKEND_DL=ON \
    -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --config Release --target llama-server -j$(nproc)

# ------------------------------------------------------------------------------
# STAGE 2: Runtime
# We use the NVIDIA runtime image (not base) because the CUDA backend requires
# cuBLAS (libcublas.so.12) which is only present in the runtime tier and above.
# ------------------------------------------------------------------------------
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV LD_LIBRARY_PATH=/usr/local/lib

# Install CPU parallelization and networking libraries
RUN apt-get update && apt-get install -y \
    libcurl4 \
    libgomp1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /models

# Copy the core server binary
COPY --from=builder /app/build/bin/llama-server /usr/local/bin/llama-server

# Copy shared libraries (libllama.so, libggml.so, etc.) for ldconfig
COPY --from=builder /app/build/bin/lib*.so* /usr/local/lib/

RUN ldconfig

# llama-server with GGML_BACKEND_DL=ON searches for backend plugins in its
# own directory at runtime. Copy the CPU and CUDA backend plugins there.
RUN cp /usr/local/lib/libggml-cpu.so /usr/local/bin/ && \
    (cp /usr/local/lib/libggml-cuda.so /usr/local/bin/ 2>/dev/null || true)

EXPOSE 8080

ENTRYPOINT ["llama-server", "--host", "0.0.0.0", "--port", "8080"]
CMD ["--help"]
