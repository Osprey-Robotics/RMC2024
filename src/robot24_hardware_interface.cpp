/** Copyright 2023 Osprey Robotics - UNF
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 */

#include <chrono>
#include <cmath>
#include <cstddef>
#include <limits>
#include <memory>
#include <vector>

#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "rclcpp/rclcpp.hpp"

#include "robot24_hardware_interface.hpp"

namespace robot24_hardware_interface
{
    hardware_interface::CallbackReturn Robot24SystemHardware::on_init(
        const hardware_interface::HardwareInfo &info)
    {
        if (hardware_interface::SystemInterface::on_init(info) !=
            hardware_interface::CallbackReturn::SUCCESS)
        {
            return hardware_interface::CallbackReturn::ERROR;
        }

        robot_ = osprey_robotics::Robot();

        // need to add try/catch for missing params, blows up otherwise
        hw_start_sec_ = std::stod(info_.hardware_parameters["hw_start_duration_sec"]);
        hw_stop_sec_ = std::stod(info_.hardware_parameters["hw_stop_duration_sec"]);

        // Resize vectors
        hw_states_.resize(info_.joints.size(), std::numeric_limits<double>::quiet_NaN());
        hw_commands_.resize(info_.joints.size(), std::numeric_limits<double>::quiet_NaN());
        hw_positions_.resize(info_.joints.size(), std::numeric_limits<double>::quiet_NaN());
        hw_velocities_.resize(info_.joints.size(), std::numeric_limits<double>::quiet_NaN());

        for (const hardware_interface::ComponentInfo &joint : info_.joints)
        {
            // Robot has exactly two states and one command interface on each joint
            if (joint.command_interfaces.size() != 1)
            {
                RCLCPP_FATAL(rclcpp::get_logger(CLASS_NAME),
                             "Joint '%s' has %zu command interfaces found. 1 expected.",
                             joint.name.c_str(),
                             joint.command_interfaces.size());
                return hardware_interface::CallbackReturn::ERROR;
            }

            if (joint.name.find("wheel") != std::string::npos &&
                joint.command_interfaces[0].name != hardware_interface::HW_IF_VELOCITY)
            {
                RCLCPP_FATAL(rclcpp::get_logger(CLASS_NAME),
                             "Joint '%s' have %s command interfaces found. '%s' expected.",
                             joint.name.c_str(),
                             joint.command_interfaces[0].name.c_str(),
                             hardware_interface::HW_IF_VELOCITY);
                return hardware_interface::CallbackReturn::ERROR;
            }

            if (joint.name.find("wheel") != std::string::npos &&
                joint.state_interfaces.size() != 2)
            {
                RCLCPP_FATAL(rclcpp::get_logger(CLASS_NAME),
                             "Joint '%s' has %zu state interface. 2 expected.",
                             joint.name.c_str(),
                             joint.state_interfaces.size());
                return hardware_interface::CallbackReturn::ERROR;
            }

            if (joint.state_interfaces[0].name != hardware_interface::HW_IF_POSITION)
            {
                RCLCPP_FATAL(rclcpp::get_logger(CLASS_NAME),
                             "Joint '%s' have '%s' as first state interface. '%s' expected.",
                             joint.name.c_str(),
                             joint.state_interfaces[0].name.c_str(),
                             hardware_interface::HW_IF_POSITION);
                return hardware_interface::CallbackReturn::ERROR;
            }

            if (joint.name.find("wheel") != std::string::npos &&
                joint.state_interfaces[1].name != hardware_interface::HW_IF_VELOCITY)
            {
                RCLCPP_FATAL(rclcpp::get_logger(CLASS_NAME),
                             "Joint '%s' have '%s' as second state interface. '%s' expected.",
                             joint.name.c_str(),
                             joint.state_interfaces[1].name.c_str(),
                             hardware_interface::HW_IF_VELOCITY);
                return hardware_interface::CallbackReturn::ERROR;
            }
        }

        return hardware_interface::CallbackReturn::SUCCESS;
    }

    std::vector<hardware_interface::StateInterface> Robot24SystemHardware::export_state_interfaces()
    {
        std::vector<hardware_interface::StateInterface> state_interfaces;

        // joints
        for (auto i = 0u; i < info_.joints.size(); i++)
        {
            state_interfaces.emplace_back(
                hardware_interface::StateInterface(info_.joints[i].name,
                                                   hardware_interface::HW_IF_POSITION,
                                                   &hw_positions_[i]));
            state_interfaces.emplace_back(
                hardware_interface::StateInterface(info_.joints[i].name,
                                                   hardware_interface::HW_IF_VELOCITY,
                                                   &hw_velocities_[i]));
        }
        return state_interfaces;
    }

    std::vector<hardware_interface::CommandInterface> Robot24SystemHardware::export_command_interfaces()
    {
        std::vector<hardware_interface::CommandInterface> command_interfaces;

        // joints
        for (auto i = 0u; i < info_.joints.size(); i++)
        {
            if (info_.joints[i].name.find("wheel") != std::string::npos)
            {
                command_interfaces.emplace_back(
                    hardware_interface::CommandInterface(info_.joints[i].name,
                                                        hardware_interface::HW_IF_VELOCITY,
                                                        &hw_commands_[i]));
            }
            else
            {
                command_interfaces.emplace_back(
                    hardware_interface::CommandInterface(info_.joints[i].name,
                                                        hardware_interface::HW_IF_POSITION,
                                                        &hw_commands_[i]));
            }
        }

        return command_interfaces;
    }

    hardware_interface::CallbackReturn Robot24SystemHardware::on_activate(
        const rclcpp_lifecycle::State & /*previous_state*/)
    {
        RCLCPP_INFO(rclcpp::get_logger(CLASS_NAME), "Activating ...please wait...");

        for (auto i = 0; i < hw_start_sec_; i++)
        {
            rclcpp::sleep_for(std::chrono::seconds(1));
            RCLCPP_INFO(rclcpp::get_logger(CLASS_NAME),
                        "%.1f seconds left...", hw_start_sec_ - i);
        }

        // set default values
        for (auto i = 0u; i < hw_positions_.size(); i++)
        {
            if (std::isnan(hw_positions_[i]))
            {
                hw_positions_[i] = 0;
                hw_velocities_[i] = 0;
                hw_commands_[i] = 0;
            }
        }

        RCLCPP_INFO(rclcpp::get_logger(CLASS_NAME), "Successfully activated!");

        return hardware_interface::CallbackReturn::SUCCESS;
    }

    hardware_interface::CallbackReturn Robot24SystemHardware::on_deactivate(
        const rclcpp_lifecycle::State & /*previous_state*/)
    {
        RCLCPP_INFO(rclcpp::get_logger(CLASS_NAME), "Deactivating ...please wait...");

        for (auto i = 0; i < hw_stop_sec_; i++)
        {
            rclcpp::sleep_for(std::chrono::seconds(1));
            RCLCPP_INFO(rclcpp::get_logger(CLASS_NAME),
                        "%.1f seconds left...", hw_stop_sec_ - i);
        }

        RCLCPP_INFO(rclcpp::get_logger(CLASS_NAME), "Successfully deactivated!");

        return hardware_interface::CallbackReturn::SUCCESS;
    }

    hardware_interface::return_type Robot24SystemHardware::read(
        const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
    {
        for (std::size_t i = 0; i < hw_velocities_.size(); i++)
        {
            osprey_robotics::Joint joint = robot_.getJoint(info_.joints[i].name);
        }

        return hardware_interface::return_type::OK;
    }

    hardware_interface::return_type robot24_hardware_interface::Robot24SystemHardware::write(
        const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
    {
        for (auto i = 0u; i < info_.joints.size(); i++)
        {
            uint8_t duration = 1;

            osprey_robotics::Joint joint = robot_.getJoint(info_.joints[i].name);

            if (info_.joints[i].name.find("right_wheel") != std::string::npos)
                hw_commands_[i] = -hw_commands_[i];

            hw_velocities_[i] = hw_commands_[i];

            // Commands sent to hardware
            RCLCPP_DEBUG(rclcpp::get_logger(CLASS_NAME),
                         "Joint: %s, command %.5f, position state: %.5f, velocity state: %.5f",
                         info_.joints[i].name.c_str(),
                         hw_commands_[i],
                         hw_positions_[i],
                         hw_velocities_[i]);

            joint.actuate(hw_commands_[i], duration);
        }

        return hardware_interface::return_type::OK;
    }

}

#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(robot24_hardware_interface::Robot24SystemHardware,
                       hardware_interface::SystemInterface)
