import {users} from "./DemoUser.js";
import {ethers} from "ethers";
import {contractAddress, contractAbi} from "./ContractData.js";
import {buildPoseidon} from "circomlibjs";
dotenv.config();

//Kết nối đến hợp đồng Voting đã triển khai
const provider = new ethers.providers.JsonRpcProvider(
    process.env.SEPOLIA_RPC_URL
);
const privateKey = process.env.PRIVATE_KEY;
const wallet = new ethers.Wallet(privateKey, provider);

const votingContract = new ethers.Contract(
    contractAddress,
    contractAbi,
    wallet
);
console.log("Connected to Voting contract at:", votingContract);

async function demoVote(candidateIndex) {
    // Khi bắt đầu một cuộc bầu cử mới, mỗi cử tri sẽ được cấp
    // một secret duy nhất và một nullifierTrapdoor.

    const userSecret = users[0].secret;
    const userNullifierTrapdoor = users[0].nullifierTrapdoor;

    // Các thông tin cần thiết về cuộc bầu cử sẽ được public từ
    // hợp đồng thông minh, bao gồm electionId, merkleRoot và numCandidates.
    const electionInfo = await votingContract.getElectionInfo();
    const electionId = electionInfo._electionId;
    const merkleRoot = electionInfo._merkleRoot;
    const numCandidates = electionInfo._numCandidates;
    try {
    } catch (error) {
        console.error("Error in demoScript:", error);
    }
}

demoScript();
