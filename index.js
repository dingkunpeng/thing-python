#!/usr/bin/env node

const args = process.argv.slice(2);
let shouldShout = false;
let parsingOptions = true;
const names = [];

for (const arg of args) {
  if (parsingOptions && arg === '--') {
    parsingOptions = false;
    continue;
  }

  if (parsingOptions && arg === '--shout') {
    shouldShout = true;
    continue;
  }

  names.push(arg);
}

const name = names[0] || 'World';
let greeting = `Hello, ${name}!`;

if (shouldShout) {
  greeting = greeting.toUpperCase();
}

console.log(greeting);
