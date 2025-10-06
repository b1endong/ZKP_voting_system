// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
import {Groth16Verifier} from "./verifier.sol";

contract Voting {
    Groth16Verifier verifier;
    address public owner;
    uint256 public electionId;
    bytes32 public merkleRoot;
    uint256 public numCandidates;
    mapping(uint256 => bool) public nullifierHashes;

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
    }
}
