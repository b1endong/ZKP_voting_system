pragma circom 2.0.0;
include "../../node_modules/circomlib/circuits/poseidon.circom";
include "../../node_modules/circomlib/circuits/comparators.circom";

/*//////////////////////////////////////////////////////////////
                    POSEIDON HASH FUNCTION
//////////////////////////////////////////////////////////////*/

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

template VotingCircuit(depth, numCandidates){

    /*//////////////////////////////////////////////////////////////
                         PRIVATE INPUT SIGNALS
    //////////////////////////////////////////////////////////////*/

    signal input secret;
    signal input nullifierTrapdoor;
    signal input vote[numCandidates]; // One-hot encoded vote
    signal input randomness;          // nonce for commitment
    signal input pathElements[depth];
    signal input pathIndices[depth];

    /*//////////////////////////////////////////////////////////////
                          PUBLIC INPUT SIGNALS
    //////////////////////////////////////////////////////////////*/

    signal input electionId;
    signal input merkleRoot;
    signal input commitment;

    /*//////////////////////////////////////////////////////////////
                         PUBLIC OUTPUT SIGNALS
    //////////////////////////////////////////////////////////////*/

    signal output nullifierHash; 

    /*//////////////////////////////////////////////////////////////
                   CREATE PUBLIC KEY FROM SECRET KEY
    //////////////////////////////////////////////////////////////*/

    component h1 = poseidonHash1();
    h1.in <== secret;
    signal leaf;
    leaf <== h1.out;

    /*//////////////////////////////////////////////////////////////
                          COMPUTE MERKLE ROOT
    //////////////////////////////////////////////////////////////*/

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

    /*//////////////////////////////////////////////////////////////
              COMPUTE ROOT MUST MATCHES THE PROVIDED ROOT
    //////////////////////////////////////////////////////////////*/

    curr[depth] === merkleRoot;
    
    /*//////////////////////////////////////////////////////////////
                  VOTE VALIDATION
    //////////////////////////////////////////////////////////////*/

    // Ensure that vote is one-hot encoded (i.e., exactly one entry is 1, rest are 0) [0,0,1,0,...]
    signal sumVotes;
    sumVotes <== 0;
    for (var j = 0; j < numCandidates; j++) {
        votes[j] * (votes[j] - 1) === 0; // boolean
        sumVotes <== sumVotes + votes[j];
    }
    sumVotes === 1;

    /*//////////////////////////////////////////////////////////////
                            COMMITMENT CHECK
    //////////////////////////////////////////////////////////////*/

    component commHash = Poseidon(numCandidates + 1);
    for (var k = 0; k < numCandidates; k++) {
        commHash.inputs[k] <== votes[k];
    }
    commHash.inputs[numCandidates] <== randomness;
    signal computedCommit;
    computedCommit <== commHash.out;

    // Enforce the computed commitment equals the public commitment input
    computedCommit === commitment;

    /*//////////////////////////////////////////////////////////////
                  NULLIFIER HASH COMPUTATION
    //////////////////////////////////////////////////////////////*/

    component poseidon3 = Poseidon(2);
    poseidon3.inputs[0] <== nullifierTrapdoor;
    poseidon3.inputs[1] <== electionId;
    nullifierHash <== poseidon3.out; 
}
component main = VotingCircuit(2,4); // Example with depth 2 and 4 candidates