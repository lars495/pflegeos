FROM nginx:1.27-alpine

COPY index.html /usr/share/nginx/html/index.html
COPY styles.css /usr/share/nginx/html/styles.css
COPY contribute.js /usr/share/nginx/html/contribute.js

# Lauscht auf Port 3000, damit nginx-Reverse-Proxy einheitlich proxen kann
RUN sed -i 's/listen       80;/listen       3000;/' /etc/nginx/conf.d/default.conf

EXPOSE 3000
