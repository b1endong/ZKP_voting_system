// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {Script} from "forge-std/Script.sol";
import {Voting} from "../src/Voting.sol";
import {Groth16Verifier} from "../src/verifier.sol";
import {Updater} from "../src/Updater.sol";

contract DeployVoting is Script {
    function run() external {
        vm.startBroadcast();

        // --- BẮT ĐẦU SỬA TẠI ĐÂY ---
        // 1. Di chuyển logic tạo mảng vào TRONG hàm run()
        address[] memory validators = new address[](5);
        validators[0] = 0x3C0174e25E866C3CE93DEb4883fAAf09e094CA72;
        validators[1] = 0xD55B67EaF6B7C11C813aaa077467a889B58c17A4;
        validators[2] = 0x0da9610F6B11F5Bf09DE393960a017b481CDfea2;
        validators[3] = 0x4E08134c891B54B0cca3b9C87F95Df146324ca7F;
        validators[4] = 0x2B182d40098E81481FD234Fa6D29Ab847A2d328a;

        // 2. Deploy contracts
        Groth16Verifier verifier = new Groth16Verifier();

        // Deploy Updater với mảng validators vừa tạo
        Updater lightClient = new Updater(
            validators,
            3,
            0x0000000000000000000000000000000000000000000000000000000000000000
        ); // Threshold = 2 (ví dụ)

        // Deploy Voting
        new Voting(
            address(verifier),
            address(lightClient),
            42, // Election ID
            4 // Num Candidates
        );
        // --- KẾT THÚC SỬA ---

        vm.stopBroadcast();
    }
}
