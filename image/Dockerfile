FROM ghcr.io/tidewell-labs/pebble@sha256:03a64abc8a975abb028e72f080237f345654d5bd33a6bcf640604d4c015295d6
RUN /usr/local/bin/python -m pip install --no-cache-dir --no-deps beautifulsoup4==4.15.0 cffi==2.1.1 curl_cffi==0.16.3 lxml==6.1.3 multitasking==0.0.13 peewee==4.5.1 platformdirs==4.11.8 protobuf==7.36.1 pycparser==3.0 pytz==2026.3.post1 soupsieve==2.9.2 websockets==17.1 yfinance==1.7.0 && /usr/local/bin/python -m pip check
COPY solve.py mini_driver.py solver_agent_v205l.py peek_data_v7.py /opt/
COPY msw /opt/msw
COPY msw_session /opt/msw_session
COPY qfref /opt/qfref
ENTRYPOINT ["/usr/local/bin/python", "/opt/solve.py"]
