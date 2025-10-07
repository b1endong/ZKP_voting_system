// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {Groth16Verifier} from "../src/verifier.sol";
import {Voting} from "../src/Voting.sol";
import "forge-std/Script.sol";

contract DeployVoting is Script {
    Voting private voting;
    Groth16Verifier private verifier;
    uint256 constant electionId = 42;
    bytes32 constant merkleRoot =
        bytes32(
            (
                uint256(
                    16913408437976580737476875716108326861435185907917839778183277611231320791399
                )
            )
        );

    uint256 constant numCandidates = 4;

    function run() external returns (Voting) {
        vm.startBroadcast();
        //Deploy Verifier Contract
        verifier = new Groth16Verifier();
        //Deploy Voting Contract
        voting = new Voting(
            address(verifier),
            electionId,
            merkleRoot,
            numCandidates
        );
        vm.stopBroadcast();
        return voting;
    }
}
