ARG BASE=base:amd64
FROM ${BASE}

LABEL qfbench2.interface_version="2.0"

RUN python -m venv /opt/agent && /opt/agent/bin/pip install --no-cache-dir mini-swe-agent==2.4.6 \
    && /opt/agent/bin/python -c "import minisweagent, litellm" \
    && python -c "import pandas, numpy; assert pandas.__version__ == '3.0.5'; assert numpy.__version__ == '2.5.3'"

ENV LITELLM_LOCAL_MODEL_COST_MAP=True \
    MSWEA_COST_TRACKING=ignore_errors \
    MSWEA_SILENT_STARTUP=1 \
    MSWEA_CONFIGURED=true \
    MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT=2 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp \
    XDG_CONFIG_HOME=/tmp/.config \
    XDG_CACHE_HOME=/tmp/.cache \
    MPLCONFIGDIR=/tmp/.matplotlib \
    NUMBA_CACHE_DIR=/tmp/.numba \
    HF_HOME=/tmp/.hf

COPY solve.py agent.py /opt/

WORKDIR /app

ENTRYPOINT ["/opt/agent/bin/python", "/opt/solve.py"]
CMD ["solve"]
