import {groth16} from "snarkjs";
import * as fs from "fs/promises";
import path from "path";
import {fileURLToPath} from "url";

// Get the directory of the current script
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 1. Get the input file path from the command line
const inputFilePath = process.argv[2] || path.join(__dirname, "input.json");
if (!inputFilePath) {
    console.error("Error: Please provide a path to the input.json file.");
    process.exit(1);
}

// 2. Read and parse inputs from Python/File
const inputs = JSON.parse(await fs.readFile(inputFilePath, "utf-8"));

console.log("Generating proof for inputs:", inputs);

try {
    // 3. Generate the proof
    // Ensure paths to .wasm and .zkey are correct relative to this script
    const {proof, publicSignals} = await groth16.fullProve(
        inputs,
        path.join(__dirname, "../zkp_proof/voting_js/voting.wasm"), // Adjusted path assumption
        path.join(__dirname, "../zkp_proof/voting_0001.zkey") // Adjusted path assumption
    );

    // 4. Export Solidity Call Data
    // This is crucial: It ensures Public Signals are in the order the Contract expects
    const calldata = await groth16.exportSolidityCallData(proof, publicSignals);
    console.log("Solidity Call Data generated.");

    // 5. Format the data for Solidity/Python
    // We pass 'calldata' string to our helper to parse it into arrays
    const formattedProof = formatProofForSolidity(calldata);

    // 6. Create the final object to save
    const outputJson = {
        // Raw SnarkJS data (optional, good for debugging)
        proof: proof,
        rawPublicSignals: publicSignals,

        // Formatted data for Solidity (a, b, c, inputs)
        // This solves your "log != expected log" error by ensuring correct order
        a: formattedProof.a,
        b: formattedProof.b,
        c: formattedProof.c,
        inputs: formattedProof.inputs, // This is the correctly ordered public signals array
    };

    // 7. Write the proof back
    await fs.writeFile(
        path.join(__dirname, "proof.json"),
        JSON.stringify(outputJson, null, 2)
    );

    console.log("Proof generated successfully: proof.json");
    process.exit(0);
} catch (err) {
    console.error("Error during proof generation:", err);
    process.exit(1);
}

/**
 * Helper to parse the generic string returned by snarkjs into structured arrays
 */
function formatProofForSolidity(calldata) {
    // Remove quotes, brackets, and whitespace to get a clean list of hex strings
    const argv = calldata.replace(/["[\]\s]/g, "").split(",");

    // Parse A: [uint256, uint256]
    const a = [argv[0], argv[1]];

    // Parse B: [[uint256, uint256], [uint256, uint256]]
    // Note: output from snarkjs is flat in argv, so we reconstruct the structure
    const b = [
        [argv[2], argv[3]],
        [argv[4], argv[5]],
    ];

    // Parse C: [uint256, uint256]
    const c = [argv[6], argv[7]];

    // Parse Inputs: Everything after index 7
    // This array will contain [Nullifier, ElectionID, MerkleRoot, Commitment] in correct order
    const inputs = argv.slice(8);

    return {
        a,
        b,
        c,
        inputs,
    };
}
