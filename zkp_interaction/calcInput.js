import {buildPoseidon} from "circomlibjs";
import users from "./users.js";
import fs from "fs";
import path from "path";
import {fileURLToPath} from "url";

// Get the directory of the current script
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log(__dirname);
console.log(__filename);

// Initialize Poseidon hash function

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

// Manual Merkle tree construction with depth 10
const DEPTH = 10;
const NUM_CANDIDATES = 4;

const merkleTree = buildMerkleTree(leaves);
const merkleRoot = merkleTree[merkleTree.length - 1][0];
console.log("Merkle Root:", merkleRoot.toString());

const proofIndex = 2;
const user = users[proofIndex];
// Lấy proof
const {pathElements, pathIndices} = getMerkleProof(proofIndex, merkleTree);
console.log("Proof for user", proofIndex, ":");
console.log("PathElements:", pathElements);
console.log("PathIndices:", pathIndices);

// Generate nullifier hash (like in circuit)
const electionId = "42"; // Example election ID
const nullifierHash = poseidonHash2(user.nullifierTrapdoor, electionId);

// Generate commitment (like in circuit)
const randomness = BigInt(123456); // Example randomness
const voteIndex = 1; // Bỏ phiếu cho ứng viên thứ 1 (0-indexed)

// Tạo mảng phiếu bầu (one-hot encoded)
const votes = Array(NUM_CANDIDATES).fill(BigInt(0));
if (voteIndex < NUM_CANDIDATES) {
    votes[voteIndex] = BigInt(1);
}

// Băm nối tiếp (Chained Hashing) - Giống hệt logic trong Circom
let currentHashState = randomness;
for (let k = 0; k < NUM_CANDIDATES; k++) {
    currentHashState = poseidonHash2(currentHashState, votes[k]);
}
const commitment = currentHashState;

const solidity_Merkle =
    "0x" + BigInt(merkleRoot).toString(16).padStart(64, "0");

// Create input object for the circuit
const input = {
    // Private inputs
    secret: user.secret,
    nullifierTrapdoor: user.nullifierTrapdoor,
    vote: votes.map((v) => v.toString()), // Mảng 1024 phần tử
    randomness: randomness.toString(),
    pathElements: pathElements, // Mảng 10 phần tử
    pathIndices: pathIndices, // Mảng 10 phần tử

    // Public inputs (phải khớp với public.json)
    // Lưu ý: Circom nhận Merkle Root là SỐ (string decimal), không phải hex
    merkleRoot: merkleRoot.toString(),
    electionId: electionId,
    commitment: commitment.toString(),
};

console.log("\nGenerated input for circuit:");
console.log(JSON.stringify(input, null, 2));

export default input;

// // Write input to input.json file
// fs.writeFileSync(
//     path.join(__dirname, "input.json"),
//     JSON.stringify(input, null, 2)
// );
// console.log("\nInput saved to input.json");

function buildMerkleTree(leaves) {
    if (leaves.length === 0) {
        return [[BigInt(0)]]; // Cây rỗng
    }

    const tree = [leaves];
    let currentLevel = leaves;

    while (currentLevel.length > 1) {
        const nextLevel = [];
        for (let i = 0; i < currentLevel.length; i += 2) {
            const left = currentLevel[i];
            // Nếu không có nút phải, gán là 0
            const right =
                i + 1 < currentLevel.length ? currentLevel[i + 1] : BigInt(0);

            let parent;
            if (right === BigInt(0)) {
                parent = left; // LOGIC QUAN TRỌNG: Đẩy node lên (giống Circom)
            } else {
                parent = poseidonHash2(left, right);
            }
            nextLevel.push(parent);
        }
        tree.push(nextLevel);
        currentLevel = nextLevel;
    }
    return tree;
}

// Lấy Merkle proof và pad 0 cho đủ DEPTH
function getMerkleProof(leafIndex, tree) {
    const pathElements = [];
    const pathIndices = [];
    let currentIndex = leafIndex;

    // Lấy proof từ cây (chỉ đến độ cao thực tế của cây)
    for (let level = 0; level < tree.length - 1; level++) {
        const levelNodes = tree[level];
        const isRightChild = currentIndex % 2 === 1;
        const siblingIndex = isRightChild ? currentIndex - 1 : currentIndex + 1;

        pathIndices.push(isRightChild ? 1 : 0);

        let siblingHash;
        if (siblingIndex < levelNodes.length) {
            siblingHash = levelNodes[siblingIndex];
        } else {
            siblingHash = BigInt(0); // Sibling là 0 (nút rỗng)
        }
        pathElements.push(siblingHash.toString());
        currentIndex = Math.floor(currentIndex / 2);
    }

    // Pad 0 vào proof cho đến khi đủ DEPTH (bắt buộc cho Circom)
    while (pathElements.length < DEPTH) {
        pathElements.push("0");
        pathIndices.push(0);
    }

    return {pathElements, pathIndices};
}
