import gplay from "google-play-scraper";

// gplay.datasafety({appId: "com.cupidmedia.wrapper.militarycupid"}).then(console.log);

import fs from 'node:fs';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function processLineByLine() {
  try {
    // const fileStream = fs.createReadStream(path.join(__dirname, 'final_package_names.csv'));
    const fileStream = fs.createReadStream(path.join(__dirname, 'nonMM_package_names.csv'));

    const rl = readline.createInterface({
      input: fileStream,
      crlfDelay: Infinity,
    });

    rl.on('line', (line) => {
      console.log(`Line from file: ${line}`);
	gplay.datasafety({appId: line}).then((value) => {
		console.log(line);
		console.log(value);
	});
    });

    await new Promise((resolve) => {
      rl.on('close', resolve);
    });

    console.log('Reading file line by line complete.');
  } catch (err) {
    console.error(err);
  }
}

processLineByLine();
