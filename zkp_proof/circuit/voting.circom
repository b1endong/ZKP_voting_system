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
    ////////////////////////////////////////////////////////////////*/
    component h1 = poseidonHash1();
    h1.in <== secret;
    signal leaf;
    leaf <== h1.out;

    /*//////////////////////////////////////////////////////////////
                          COMPUTE MERKLE ROOT
    //////////////////////////////////////////////////////////////*/

component h2[depth];
    component isZero[depth];
    signal curr[depth + 1];
    signal left[depth];
    signal right[depth];
    signal computedHash[depth]; // Hash tạm thời

    curr[0] <== leaf;
    
    for (var i = 0; i < depth; i++) {
        // 1. Tính toán hash (như bình thường)
        h2[i] = poseidonHash2();
        left[i] <== curr[i] + pathIndices[i] * (pathElements[i] - curr[i]);
        right[i] <== pathElements[i] + pathIndices[i] * (curr[i] - pathElements[i]);
        h2[i].in1 <== left[i];
        h2[i].in2 <== right[i];
        computedHash[i] <== h2[i].out;
        
        // 2. Kiểm tra xem sibling (pathElements[i]) có bằng 0 không
        isZero[i] = IsZero();
        isZero[i].in <== pathElements[i];
        
        // 3. Chọn node tiếp theo
        // Nếu sibling = 0 (isZero.out=1), node tiếp theo = node hiện tại
        // Nếu sibling != 0 (isZero.out=0), node tiếp theo = hash vừa tính
        curr[i + 1] <== curr[i] + (1 - isZero[i].out) * (computedHash[i] - curr[i]);
    }

    /*//////////////////////////////////////////////////////////////
              COMPUTE ROOT MUST MATCHES THE PROVIDED ROOT
    //////////////////////////////////////////////////////////////*/

    curr[depth] === merkleRoot;
    
    /*//////////////////////////////////////////////////////////////
                  VOTE VALIDATION
    //////////////////////////////////////////////////////////////*/

    // Ensure that vote is one-hot encoded (i.e., exactly one entry is 1, rest are 0) [0,0,1,0,...]
    signal votes[numCandidates];
    signal voteSum[numCandidates + 1];
    voteSum[0] <== 0;
    for (var j = 0; j < numCandidates; j++) {
        votes[j] <== vote[j];
        votes[j] * (votes[j] - 1) === 0; // boolean
        voteSum[j + 1] <== voteSum[j] + votes[j];
        }
    voteSum[numCandidates] === 1;

    /*//////////////////////////////////////////////////////////////
                            COMMITMENT CHECK
    //////////////////////////////////////////////////////////////*/

    component voteHasher[numCandidates];
    signal voteHashState[numCandidates + 1];

    // Khởi tạo hash state bằng randomness (đóng vai trò là Salt/Nonce)
    voteHashState[0] <== randomness;

    for (var k = 0; k < numCandidates; k++) {
        voteHasher[k] = Poseidon(2);
        voteHasher[k].inputs[0] <== voteHashState[k];
        voteHasher[k].inputs[1] <== votes[k];
        voteHashState[k+1] <== voteHasher[k].out;
    }

    signal computedCommit;
    computedCommit <== voteHashState[numCandidates];

    computedCommit === commitment;

    /*//////////////////////////////////////////////////////////////
                  NULLIFIER HASH COMPUTATION
    //////////////////////////////////////////////////////////////*/

    component poseidon3 = Poseidon(2);
    poseidon3.inputs[0] <== nullifierTrapdoor;
    poseidon3.inputs[1] <== electionId;
    nullifierHash <== poseidon3.out; 
}
component main {public [electionId, merkleRoot, commitment]} = VotingCircuit(10,100); // Example with depth 10 and 100 candidates