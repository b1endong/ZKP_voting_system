import {buildPoseidon} from "circomlibjs";
import users from "./users.js";
import fs from "fs";

const poseidon = await buildPoseidon();
const F = poseidon.F;

// Hash function using Poseidon for single input (like poseidonHash1 in circuit)
function poseidonHash1(data) {
    return F.toObject(poseidon([BigInt(data)]));
}

// Hash function using Poseidon for two inputs (like poseidonHash2 in circuit)
function poseidonHash2(left, right) {
    return F.toObject(poseidon([BigInt(left), BigInt(right)]));
}

// Create leaves by hashing user secrets using poseidonHash1 (same as circuit)
const leaves = users.map((user) => poseidonHash1(user.secret));
console.log(
    "Leaves:",
    leaves.map((leaf) => leaf.toString())
);

// Manual Merkle tree construction with depth 2
const depth = 2;

// For a tree with depth 2, we need 4 leaves (2^2 = 4)
// Pad with zeros if we don't have enough leaves
while (leaves.length < Math.pow(2, depth)) {
    leaves.push(BigInt(0));
}

// Build tree level by level
let currentLevel = [...leaves];
const tree = [currentLevel];

for (let level = 0; level < depth; level++) {
    const nextLevel = [];
    for (let i = 0; i < currentLevel.length; i += 2) {
        const left = currentLevel[i];
        const right = currentLevel[i + 1] || BigInt(0);
        const hash = poseidonHash2(left, right);
        nextLevel.push(hash);
    }
    tree.push(nextLevel);
    currentLevel = nextLevel;
}

const merkleRoot = currentLevel[0];
console.log("Merkle Root:", merkleRoot.toString());

// Generate proof for the first user (index 0)
const userIndex = 0;
const user = users[userIndex];

// Calculate path elements and indices
const pathElements = [];
const pathIndices = [];

let currentIndex = userIndex;
for (let level = 0; level < depth; level++) {
    const isRightChild = currentIndex % 2 === 1;
    const siblingIndex = isRightChild ? currentIndex - 1 : currentIndex + 1;

    // Get sibling element
    const siblingElement = tree[level][siblingIndex] || BigInt(0);
    pathElements.push(siblingElement.toString());

    // Path index: 0 if current is left child, 1 if current is right child
    pathIndices.push(isRightChild ? 1 : 0);

    currentIndex = Math.floor(currentIndex / 2);
}

console.log("Proof for user", userIndex, ":");
console.log("PathElements:", pathElements);
console.log("PathIndices:", pathIndices);

// Generate nullifier hash (like in circuit)
const electionId = "42"; // Example election ID
const nullifierHash = poseidonHash2(user.nullifierTrapdoor, electionId);

// Generate commitment (like in circuit)
const randomness = BigInt(123456); // Example randomness
const votes = [0, 1, 0, 0];
const commitmentInputs = [...votes.map((v) => BigInt(v)), randomness];
const commitment = F.toObject(poseidon(commitmentInputs));

// Create input object for the circuit
const input = {
    secret: user.secret,
    nullifierTrapdoor: user.nullifierTrapdoor,
    vote: votes,
    randomness: randomness.toString(),
    commitment: commitment.toString(),
    pathElements: pathElements,
    pathIndices: pathIndices,
    electionId: electionId,
    merkleRoot: merkleRoot.toString(),
};

console.log("\nGenerated input for circuit:");
console.log(JSON.stringify(input, null, 2));

// Write input to input.json file
fs.writeFileSync("input/input.json", JSON.stringify(input, null, 2));
console.log("\nInput saved to input.json");
