import {users} from "./DemoUser.js";
import {ethers} from "ethers";
import {contractAddress, contractAbi} from "./ContractData.js";
import {buildPoseidon} from "circomlibjs";
import {groth16} from "snarkjs";
import dotenv from "dotenv";
dotenv.config({
    path: "../.env",
});

//Kết nối đến hợp đồng Voting đã triển khai
const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);

const votingContract = new ethers.Contract(
    contractAddress,
    contractAbi,
    wallet
);
console.log("✅ Successfully connected to the Voting contract.");

// Hàm băm Poseidon
const poseidon = await buildPoseidon();
const F = poseidon.F;
function poseidonHash1(data) {
    return F.toObject(poseidon([BigInt(data)]));
}

function poseidonHash2(data1, data2) {
    return F.toObject(poseidon([BigInt(data1), BigInt(data2)]));
}

async function demoVote(candidateIndex) {
    // 1. Khi bắt đầu một cuộc bầu cử mới, mỗi cử tri sẽ được cấp
    //    một secret duy nhất và một nullifierTrapdoor.

    const userSecret = users[0].secret; // Giả sử cử tri là user đầu tiên
    const userNullifierTrapdoor = users[0].nullifierTrapdoor;
    console.log("User Secret:", userSecret);
    console.log("User Nullifier Trapdoor:", userNullifierTrapdoor);

    // 2. Các thông tin cần thiết về cuộc bầu cử sẽ được public từ
    //    hợp đồng thông minh, bao gồm electionId, merkleRoot và numCandidates.
    const electionInfo = await votingContract.getElectionInfo();
    const electionId = electionInfo._electionId;
    const merkleRoot = BigInt(electionInfo._merkleRoot);
    const numCandidates = electionInfo._numCandidates;

    console.log("Election ID:", electionId.toString());
    console.log("Merkle Root:", merkleRoot.toString());
    console.log("Number of Candidates:", numCandidates.toString());

    // 3. Tạo vote array dựa trên lựa chọn của cử tri
    const votes = Array(Number(numCandidates)).fill(0);
    votes[candidateIndex - 1] = 1;
    console.log("Votes array:", votes);

    // 4. Tạo randomness và tạo commitment
    const randomness = BigInt(Math.floor(Math.random() * 1000000));
    const commitmentInputs = [...votes.map((v) => BigInt(v)), randomness];
    const commitment = F.toObject(poseidon(commitmentInputs));
    console.log("Commitment:", commitment.toString());

    // 5. Tính cây merkle và tạo bằng chứng đường đi
    const {pathElements, pathIndices} = calcMerkleProof(0, 2); // Tạo bằng chứng cho user đầu tiên với độ sâu 2

    // 6. Tạo input cho zk-SNARK
    const zkInputs = {
        secret: userSecret,
        nullifierTrapdoor: userNullifierTrapdoor,
        vote: votes,
        randomness: randomness.toString(),
        commitment: commitment.toString(),
        pathElements: pathElements,
        pathIndices: pathIndices,
        electionId: electionId.toString(),
        merkleRoot: merkleRoot.toString(),
    };

    console.log("ZK Inputs:", zkInputs);

    // 7. Tạo zk-SNARK proof (Groth16)
    console.log("🔄 Generating ZK proof...");
    const {proof, publicSignals} = await groth16.fullProve(
        zkInputs,
        "../zkp_proof/voting_js/voting.wasm",
        "../zkp_proof/voting_0001.zkey"
    );
    console.log("✅ Proof generated successfully!");
    console.log("Proof:", proof);
    console.log("Public Signals:", publicSignals);

    // 8. Format proof cho Solidity
    const solidityProof = formatProofForSolidity(
        proof,
        publicSignals,
        commitment
    );
    console.log("Formatted proof for Solidity:", solidityProof);

    //9. Submit vote lên blockchain
    await votingContract.submitVote(
        solidityProof.a,
        solidityProof.b,
        solidityProof.c,
        solidityProof.solidity_publicSignals,
        solidityProof.solidity_commitment
    );
    console.log("✅ Vote submitted successfully!");

    try {
    } catch (error) {
        console.error("Error in demoVote:", error);
    }
}

function calcMerkleProof(_userIndex, _depth) {
    // Tạo lá (leaves) của cây Merkle từ danh sách secret của người dùng
    const leaves = users.map((user) => poseidonHash1(user.secret));

    // Đối với một cây có độ sâu 2, chúng ta cần 4 lá (2^2 = 4)
    // Thêm các giá trị 0 nếu không đủ lá
    while (leaves.length < Math.pow(2, _depth)) {
        leaves.push(BigInt(0));
    }

    // Xây dựng cây Merkle từ dưới lên
    let currentLevel = [...leaves];
    const tree = [currentLevel];

    for (let level = 0; level < _depth; level++) {
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

    // Tạo bằng chứng đường đi cho người dùng cụ thể
    const userIndex = _userIndex;
    const user = users[userIndex];

    // Tính toán các phần tử đường đi và chỉ số
    const pathElements = [];
    const pathIndices = [];

    let currentIndex = userIndex;
    for (let level = 0; level < _depth; level++) {
        const isRightChild = currentIndex % 2 === 1;
        const siblingIndex = isRightChild ? currentIndex - 1 : currentIndex + 1;

        // Lấy các phần tử anh em
        const siblingElement = tree[level][siblingIndex] || BigInt(0);
        pathElements.push(siblingElement.toString());

        // Chỉ số đường đi: 0 nếu hiện tại là nút trái, 1 nếu hiện tại là nút phải
        pathIndices.push(isRightChild ? 1 : 0);

        currentIndex = Math.floor(currentIndex / 2);
    }
    console.log("PathElements:", pathElements);
    console.log("PathIndices:", pathIndices);
    return {
        pathElements,
        pathIndices,
    };
}

function formatProofForSolidity(proof, publicSignals, commitment) {
    const a = proof.pi_a.slice(0, 2).map((x) => BigInt(x));
    const b = [
        proof.pi_b[0].slice(0, 2).map((x) => BigInt(x)),
        proof.pi_b[1].slice(0, 2).map((x) => BigInt(x)),
    ];
    const c = proof.pi_c.slice(0, 2).map((x) => BigInt(x));

    const solidity_publicSignals = [BigInt(publicSignals[0])];
    const solidity_commitment =
        "0x" + BigInt(commitment).toString(16).padStart(64, "0");
    return {a, b, c, solidity_publicSignals, solidity_commitment};
}

demoVote(2);
