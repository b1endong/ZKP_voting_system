import {MerkleTree} from "merkletreejs";
import {buildPoseidon} from "circomlibjs";
import users from "./users.js";

const poseidon = await buildPoseidon();
const F = poseidon.F;

// Hash function using Poseidon
function poseidonHash(data) {
    return F.toObject(poseidon(data));
}

// Create leaves by hashing user secrets and nullifier trapdoors
const leaves = users.map((user) => poseidonHash([BigInt(user.secret)]));
console.log(leaves[0].toString());

// Create the Merkle tree
const tree = new MerkleTree(leaves, poseidonHash);
console.log("Merkle Tree: ", BigInt(tree.getHexRoot()).toString());
console.log("Depth", tree.getDepth());

const targetLeaf = leaves[0];
const proof = tree.getProof(targetLeaf);

console.log("\nProof for user 0 (secret: 123):");
console.log("Leaf:", targetLeaf.toString());
console.log("Proof:", proof);

// Extract pathElement and pathIndices
const pathElements = proof.map((p) => p.data.toString("hex"));
const pathIndices = proof.map((p) => (p.position === "right" ? 0 : 1));

console.log("PathElements:", pathElements);
console.log("PathIndices:", pathIndices);
