FROM nginx:alpine

COPY nginx.conf /etc/nginx/nginx.conf
WORKDIR /usr/share/nginx/html
COPY index.html styles.css app.js favicon.svg ./

RUN set -eu; \
    for asset in app.js styles.css favicon.svg; do \
        hash="$(sha256sum "$asset" | cut -c1-16)"; \
        sed -i "s|$asset|$asset?v=$hash|g" index.html; \
    done; \
    gzip -k -9 index.html app.js styles.css favicon.svg

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
