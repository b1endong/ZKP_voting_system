pragma circom 2.0.0;
include "../../node_modules/circomlib/circuits/poseidon.circom";
include "../../node_modules/circomlib/circuits/comparators.circom";

template VotingCircuit(depth){
    // Private Input signals
    signal input secret;
    signal input nullifierTrapdoor;
    signal input vote; 
    signal input pathElements[depth];
    signal input pathIndices[depth];

    // Public Input signals
    signal input numCandidates;
    signal input electionId;
    signal input merkleRoot;

    // Public Output signals
    signal output nullifierHash;  

    // Hash the secret to get the public key and assign it to the leaf
    component poseidon1 = Poseidon(1);
    poseidon1.inputs[0] <== secret;
    signal leaf;
    leaf <== poseidon1.out;
    

    // Compute the Merkle root from the leaf and the path
    signal left[depth];
    signal right[depth];
    component poseidon2[depth];
    signal cur[depth + 1];
    cur[0] <== leaf;
    for (var i = 0; i < depth; i++){
        //pathIndices[i] * (pathIndices[i] - 1) === 0; // Ensure pathIndices are either 0 or 1
        left[i]  <== cur[i] + pathIndices[i] * (pathElements[i] - cur[i]);
        right[i] <== pathElements[i] + pathIndices[i] * (cur[i] - pathElements[i]);
        poseidon2[i] = Poseidon(2);  
        poseidon2[i].inputs[0] <== left[i];
        poseidon2[i].inputs[1] <== right[i];
        cur[i + 1] <== poseidon2[i].out;
    }   
    cur[depth] === merkleRoot;
    
    // 0 <= vote < numCandidates
    component comparator = LessThan(32);
    comparator.in[0] <== vote;
    comparator.in[1] <== numCandidates;
    comparator.out === 1; // Ensure vote is less than numCandidates
    
    // Compute the nullifier to prevent double voting
    component poseidon3 = Poseidon(2);
    poseidon3.inputs[0] <== nullifierTrapdoor;
    poseidon3.inputs[1] <== electionId;
    nullifierHash <== poseidon3.out; 

    
}
component main = VotingCircuit(2);