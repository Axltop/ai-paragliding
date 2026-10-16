# Launch Window: a static page. All user data lives in the visitor's browser (localStorage);
# the container only serves files and keeps no logs or state.
FROM nginxinc/nginx-unprivileged:1.27-alpine

USER root
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d
USER 101

COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/security-headers.conf /etc/nginx/security-headers.conf
COPY index.html /usr/share/nginx/html/index.html
COPY fonts/ /usr/share/nginx/html/fonts/

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
