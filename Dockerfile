FROM kpn-digital/tox:latest

RUN git config --global url."https://".insteadOf git://
RUN git config --global url."https://stash.kpnnl.local/scm".insteadOf ssh://git@stash.kpnnl.local:7999

RUN update-ca-certificates
RUN echo | openssl s_client -connect stash.kpnnl.local:443 2>&1 | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' >> /etc/ssl/certs/ca-certificates.crt

WORKDIR /app

CMD ["tox"]
