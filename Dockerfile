FROM php:8.2-cli

WORKDIR /app

# Node.js
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

EXPOSE 80

CMD ["php", "-S", "0.0.0.0:80", "-t", "."]
