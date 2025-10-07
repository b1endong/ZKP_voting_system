// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
import {Groth16Verifier} from "./verifier.sol";

contract Voting {
    Groth16Verifier verifier;
    address public owner;
    bytes32 public merkleRoot;
    uint256 public electionId;
    uint256 private randomness;
    uint256 public numCandidates;
    mapping(uint256 => bool) private nullifierUsed;
    mapping(uint256 => uint256) public voteCounts; // candidateId => voteCount
    uint256 public totalVotes;
    bool public votingEnded;

    event VoteSubmitted(address indexed voter, bytes32 commitment);

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
        bytes32 commitment
    ) external {
        require(!votingEnded, "Voting has ended");

        // Check if nullifier has been used (prevent double voting)
        require(!nullifierUsed[publicSignals[0]], "Vote already cast");

        // Verify the ZK proof
        // publicSignals[0] should be the nullifierHash from the circuit
        bool valid = verifier.verifyProof(a, b, c, publicSignals);
        require(valid, "Invalid proof");

        // Mark nullifier as used
        nullifierUsed[publicSignals[0]] = true;

        // Increment total votes
        totalVotes++;

        // Emit event with voter's commitment
        emit VoteSubmitted(msg.sender, commitment);
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

    function getVerifier() external view returns (address) {
        return address(verifier);
    }

    function getTotalVotes() external view returns (uint256) {
        return totalVotes;
    }
}
