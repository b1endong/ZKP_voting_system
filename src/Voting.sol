// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
import {Groth16Verifier} from "./verifier.sol";

contract Voting {
    Groth16Verifier verifier;
    address public owner;
    bytes32 public merkleRoot;
    uint256 private electionId;
    uint256 private randomness;
    uint256 private numCandidates;
    mapping(uint256 => bool) public nullifierUsed;
    mapping(uint256 => uint256) public voteCounts; // candidateId => voteCount
    uint256 public totalVotes;
    bool public votingEnded;

    event VoteSubmitted(address indexed voter, bytes32 commitment);
    event VotingEnded(uint256 totalVotes);
    event VoteCountRevealed(uint256 candidateId, uint256 count);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(
        address _verifier,
        uint256 _electionId,
        bytes32 _merkleRoot,
        uint256 _numCandidates
    ) {
        verifier = Groth16Verifier(_verifier);
        electionId = _electionId;
        merkleRoot = _merkleRoot;
        numCandidates = _numCandidates;
        owner = msg.sender;
    }

    function updateMerkleRoot(bytes32 _newRoot) external onlyOwner {
        merkleRoot = _newRoot;
    }

    function updateElectionId(uint256 _newId) external onlyOwner {
        electionId = _newId;
    }

    function updateRandomness(uint256 _newRandomness) external onlyOwner {
        randomness = _newRandomness;
    }

    function submitVote(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[1] calldata publicSignals,
        uint256 nullifierProvided,
        bytes32 commitment
    ) external {
        require(!votingEnded, "Voting has ended");

        // Check if nullifier has been used (prevent double voting)
        require(!nullifierUsed[nullifierProvided], "Vote already cast");

        // Verify the ZK proof
        // publicSignals[0] should be the nullifierHash from the circuit
        require(verifier.verifyProof(a, b, c, publicSignals), "Invalid proof");

        // Verify that the provided nullifier matches the one in public signals
        require(nullifierProvided == publicSignals[0], "Nullifier mismatch");

        // Mark nullifier as used
        nullifierUsed[nullifierProvided] = true;

        // Increment total votes
        totalVotes++;

        // Emit event with voter's commitment
        emit VoteSubmitted(msg.sender, commitment);
    }

    function endVoting() external onlyOwner {
        require(!votingEnded, "Voting already ended");
        votingEnded = true;
        emit VotingEnded(totalVotes);
    }

    function revealVoteCount(
        uint256 candidateId,
        uint256 count
    ) external onlyOwner {
        require(votingEnded, "Voting not ended yet");
        require(candidateId < numCandidates, "Invalid candidate ID");

        voteCounts[candidateId] = count;
        emit VoteCountRevealed(candidateId, count);
    }

    function getVoteCount(uint256 candidateId) external view returns (uint256) {
        require(votingEnded, "Voting not ended yet");
        require(candidateId < numCandidates, "Invalid candidate ID");
        return voteCounts[candidateId];
    }

    function getAllVoteCounts() external view returns (uint256[] memory) {
        require(votingEnded, "Voting not ended yet");

        uint256[] memory counts = new uint256[](numCandidates);
        for (uint256 i = 0; i < numCandidates; i++) {
            counts[i] = voteCounts[i];
        }
        return counts;
    }

    function getElectionInfo()
        external
        view
        returns (
            uint256 _electionId,
            bytes32 _merkleRoot,
            uint256 _numCandidates,
            uint256 _totalVotes,
            bool _votingEnded
        )
    {
        return (electionId, merkleRoot, numCandidates, totalVotes, votingEnded);
    }
}
