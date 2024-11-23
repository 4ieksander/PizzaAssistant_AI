FROM node:16

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173

# Komenda startowa do uruchomienia serwera deweloperskiego
CMD ["npm", "run", "dev", "--", "--host"]
