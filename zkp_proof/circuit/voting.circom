pragma circom 2.0.0;
include "../../node_modules/circomlib/circuits/poseidon.circom";
include "../../node_modules/circomlib/circuits/comparators.circom";

template poseidonHash1(){
        signal input in;
        signal output out;
        component p = Poseidon(1);
        p.inputs[0] <== in;
        out <== p.out;
    }

    template poseidonHash2(){
        signal input in1;
        signal input in2;
        signal output out;
        component p = Poseidon(2);
        p.inputs[0] <== in1;
        p.inputs[1] <== in2;
        out <== p.out;
    }

template VotingCircuit(depth){

    // Private Input signals
    signal input secret;
    signal input nullifierTrapdoor;
    signal input vote; 
    signal input pathElements[depth];
    signal input pathIndices[depth];

    // Public Input signals
    signal input electionId;
    signal input merkleRoot;

    // Public Output signals
    signal output nullifierHash; 

    // Hash the secret to get the public key and assign it to the leaf
    component h1 = poseidonHash1();
    h1.in <== secret;
    signal leaf;
    leaf <== h1.out;

    // Compute the Merkle root from the leaf and the path
    component h2[depth];
    signal curr[depth + 1];
    signal left[depth];
    signal right[depth];
    curr[0] <== leaf;
    
    for (var i = 0; i < depth; i++) {
        h2[i] = poseidonHash2();
        
        // Use intermediate signals to avoid quadratic constraints
        // pathIndices[i] should be 0 or 1
        // When pathIndices[i] == 0: left = curr[i], right = pathElements[i]  
        // When pathIndices[i] == 1: left = pathElements[i], right = curr[i]
        left[i] <== curr[i] + pathIndices[i] * (pathElements[i] - curr[i]);
        right[i] <== pathElements[i] + pathIndices[i] * (curr[i] - pathElements[i]);
        
        h2[i].in1 <== left[i];
        h2[i].in2 <== right[i];
        curr[i + 1] <== h2[i].out;
    }
    // Ensure the computed root matches the provided Merkle root    
    curr[depth] === merkleRoot;
    
    // 0 <= vote < numCandidates
        // component comparator = LessThan(32);
        // comparator.in[0] <== vote;
        // comparator.in[1] <== numCandidates;
        // comparator.out === 1; // Ensure vote is less than numCandidates
    
    vote * (vote - 1) === 0;
    // Compute the nullifier to prevent double voting
    component poseidon3 = Poseidon(2);
    poseidon3.inputs[0] <== nullifierTrapdoor;
    poseidon3.inputs[1] <== electionId;
    nullifierHash <== poseidon3.out; 
}
component main = VotingCircuit(2);