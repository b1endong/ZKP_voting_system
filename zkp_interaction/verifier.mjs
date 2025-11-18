import {groth16} from "snarkjs";
import * as fs from "fs/promises";
import path from "path";
import {fileURLToPath} from "url";

// Get the directory of the current script
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 1. Read the verification key
const vkey = JSON.parse(
    await fs.readFile("zkp_proof/verification_key.json", "utf-8")
);

// 2. Read the proof and public signals from Python
const proofObject = JSON.parse(
    await fs.readFile(path.join(__dirname, "proof.json"), "utf-8")
);

// 3. Verify the proof
const isValid = await groth16.verify(
    vkey,
    proofObject.publicSignals,
    proofObject.proof
);

// 4. Print the result for Python to capture from stdout
if (isValid) {
    console.log("TRUE");
} else {
    console.log("FALSE");
}
process.exit(0);
