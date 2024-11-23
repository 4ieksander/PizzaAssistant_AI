FROM node:16

WORKDIR /app
COPY package*.json ./
COPY . .
RUN npm install

EXPOSE 3005

CMD ["npm", "start"]
