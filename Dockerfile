FROM php:8.2-cli

WORKDIR /app

# Node.js
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 8080
EXPOSE 5177

CMD ["sh", "-c", "npm run dev -- --host --port 5177 & PID1=$!; php -S 0.0.0.0:8080 -t . & PID2=$!; wait $PID1; wait $PID2"]