// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {Groth16Verifier} from "./verifier.sol";

interface IUpdater {
    function isValidRoot(
        uint256 blockHeight,
        bytes32 merkleRoot
    ) external view returns (bool);
    function getLatestRoot() external view returns (bytes32);
    function latestBlockHeight() external view returns (uint256);
}

contract Voting {
    /*//////////////////////////////////////////////////////////////
                            STATE VARIABLES
    //////////////////////////////////////////////////////////////*/

    Groth16Verifier public immutable verifier;
    IUpdater public immutable updater;

    address public owner;
    uint256 public electionId;
    uint256 public numCandidates;

    mapping(uint256 => mapping(uint256 => bool)) private nullifierUsed;
    mapping(uint256 => uint256) public candidateVotes;
    uint256 public totalVotes;
    bool public votingEnded;

    /// @notice Deprecated: merkleRoot is now fetched from LightClient
    bytes32 private deprecated_merkleRoot;

    /*//////////////////////////////////////////////////////////////
                                EVENTS
    //////////////////////////////////////////////////////////////*/

    event VoteSubmitted(
        address indexed voter,
        bytes32 commitment,
        uint256 nullifierHash
    );
    event VotingEnded(uint256 totalVotes);
    event ElectionUpdated(uint256 newElectionId);
    event NumCandidatesUpdated(uint256 newNumCandidates);
    event VotingReopened();
    event WinnerDeclared(uint256 winnerId, uint256 winnerVotes);

    /*//////////////////////////////////////////////////////////////
                                ERRORS
    //////////////////////////////////////////////////////////////*/

    error Unauthorized();
    error VotingHasEnded();
    error AlreadyVoted();
    error InvalidProof();
    error InvalidMerkleRoot();

    /*//////////////////////////////////////////////////////////////
                            CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    constructor(
        address _verifier,
        address _updater,
        uint256 _electionId,
        uint256 _numCandidates
    ) {
        verifier = Groth16Verifier(_verifier);
        updater = IUpdater(_updater);
        electionId = _electionId;
        numCandidates = _numCandidates;
        owner = msg.sender;
    }

    /*//////////////////////////////////////////////////////////////
                            MODIFIERS
    //////////////////////////////////////////////////////////////*/

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    /*//////////////////////////////////////////////////////////////
                        ADMIN FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    function updateMerkleRoot(bytes32 _newRoot) external onlyOwner {
        deprecated_merkleRoot = _newRoot;
    }

    function endVoting() internal {
        votingEnded = true;
        emit VotingEnded(totalVotes);
    }

    function setNumCandidates(uint256 _newNumCandidates) external onlyOwner {
        require(
            _newNumCandidates > 0,
            "Number of candidates must be greater than 0"
        );
        numCandidates = _newNumCandidates;
        emit NumCandidatesUpdated(_newNumCandidates);
    }

    function resetElection() internal {
        votingEnded = false;
        totalVotes = 0;

        // Reset vote counts
        for (uint256 i = 0; i < numCandidates; i++) {
            candidateVotes[i] = 0;
        }

        // Tăng electionId để vô hiệu hóa các nullifier cũ của election trước
        electionId++;
        emit ElectionUpdated(electionId);
        emit VotingReopened();
    }

    /*//////////////////////////////////////////////////////////////
                        VOTING FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    function submitVote(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[4] calldata publicSignals, // [merkleRoot, electionId, commitment, nullifierHash]
        uint256 blockHeight,
        uint256 candidateId
    ) internal {
        if (votingEnded) revert VotingHasEnded();

        // // Extract public signals (snarkjs output order)
        uint256 nullifierHash = publicSignals[0]; // nullifierHash (output signal)
        uint256 proofElectionId = publicSignals[1]; // electionId
        bytes32 proofMerkleRoot = bytes32(publicSignals[2]); // merkleRoot
        bytes32 commitment = bytes32(publicSignals[3]); // commitment

        // Check if nullifier has been used (prevent double voting)
        if (nullifierUsed[electionId][nullifierHash]) revert AlreadyVoted();

        // Verify election ID matches
        require(proofElectionId == electionId, "Wrong election");

        require(candidateId < numCandidates, "Invalid candidate ID");

        // CRITICAL: Verify merkle root against LightClient
        // This ensures the voter was registered on Chain B at specified blockHeight
        bool rootIsValid = updater.isValidRoot(blockHeight, proofMerkleRoot);
        if (!rootIsValid) revert InvalidMerkleRoot();

        bool valid = verifier.verifyProof(a, b, c, publicSignals);
        if (!valid) revert InvalidProof();

        // Mark nullifier as used
        nullifierUsed[electionId][nullifierHash] = true;

        candidateVotes[candidateId]++;
        totalVotes++;

        emit VoteSubmitted(msg.sender, commitment, nullifierHash);

        if (totalVotes == numCandidates) {
            (uint256 winner, uint256 winnerVotes) = getWinner();
            emit WinnerDeclared(winner, winnerVotes);
            resetElection();
        }
    }

    function submitVoteLatest(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[4] calldata publicSignals,
        uint256 candidateId
    ) external {
        uint256 latestHeight = updater.latestBlockHeight();

        submitVote(a, b, c, publicSignals, latestHeight, candidateId);
    }

    /*//////////////////////////////////////////////////////////////
                        VIEW FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    function getMerkleRoot() external view returns (bytes32) {
        return updater.getLatestRoot();
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
        return (
            electionId,
            updater.getLatestRoot(), // Get from Updater instead
            numCandidates,
            totalVotes,
            votingEnded
        );
    }

    function getVerifier() external view returns (address) {
        return address(verifier);
    }

    function getUpdater() external view returns (address) {
        return address(updater);
    }

    function getTotalVotes() external view returns (uint256) {
        return totalVotes;
    }

    function hasVoted(uint256 nullifierHash) external view returns (bool) {
        return nullifierUsed[electionId][nullifierHash];
    }

    function getLatestBlockHeight() external view returns (uint256) {
        return updater.latestBlockHeight();
    }

    function getCandidateVotes(
        uint256 candidateId
    ) external view returns (uint256) {
        require(candidateId < numCandidates, "Invalid candidate ID");
        return candidateVotes[candidateId];
    }

    /// @notice Get the winning candidate (most votes)
    function getWinner()
        internal
        view
        returns (uint256 winnerId, uint256 winnerVotes)
    {
        require(totalVotes > 0, "No votes yet");

        uint256 maxVotes = 0;
        uint256 winner = 0;

        for (uint256 i = 0; i < numCandidates; i++) {
            if (candidateVotes[i] > maxVotes) {
                maxVotes = candidateVotes[i];
                winner = i;
            }
        }

        return (winner, maxVotes);
    }

    /// @notice Get all vote counts for all candidates
    function getAllVotes() external view returns (uint256[] memory) {
        uint256[] memory votes = new uint256[](numCandidates);
        for (uint256 i = 0; i < numCandidates; i++) {
            votes[i] = candidateVotes[i];
        }
        return votes;
    }
}
