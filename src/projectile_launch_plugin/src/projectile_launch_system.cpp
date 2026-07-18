#include <chrono>
#include <memory>
#include <string>

#include <gz/common/Console.hh>
#include <gz/math/Pose3.hh>
#include <gz/math/Quaternion.hh>
#include <gz/math/Vector3.hh>
#include <gz/plugin/Register.hh>
#include <gz/sim/Entity.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/Link.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>

#include <sdf/Element.hh>


namespace projectile_launch_plugin
{

class ProjectileLaunchSystem:
    public gz::sim::System,
    public gz::sim::ISystemConfigure,
    public gz::sim::ISystemPreUpdate
{
public:
    void Configure(
        const gz::sim::Entity &_entity,
        const std::shared_ptr<const sdf::Element> &_sdf,
        gz::sim::EntityComponentManager &,
        gz::sim::EventManager &) override
    {
        this->projectileModelEntity = _entity;

        if (_sdf->HasElement("reference_model"))
        {
            this->referenceModel =
                _sdf->Get<std::string>(
                    "reference_model");
        }

        if (_sdf->HasElement("reference_link"))
        {
            this->referenceLink =
                _sdf->Get<std::string>(
                    "reference_link");
        }

        if (_sdf->HasElement("local_velocity"))
        {
            this->localVelocity =
                _sdf->Get<gz::math::Vector3d>(
                    "local_velocity");
        }

        if (_sdf->HasElement("clearance"))
        {
            this->clearance =
                _sdf->Get<double>("clearance");
        }

        if (_sdf->HasElement("gravity_mps2"))
        {
            this->gravity =
                _sdf->Get<double>("gravity_mps2");
        }

        if (_sdf->HasElement("ground_z"))
        {
            this->groundZ =
                _sdf->Get<double>("ground_z");
        }

        if (_sdf->HasElement("max_flight_time"))
        {
            this->maxFlightTime =
                _sdf->Get<double>(
                    "max_flight_time");
        }

        gzmsg
            << "[ProjectileLaunchSystem] "
            << "Analitik balistik hazır | "
            << "referans="
            << this->referenceModel
            << "::"
            << this->referenceLink
            << " | yerel hız="
            << this->localVelocity
            << " m/s"
            << std::endl;
    }

    void PreUpdate(
        const gz::sim::UpdateInfo &_info,
        gz::sim::EntityComponentManager &_ecm) override
    {
        if (_info.paused || this->finished)
        {
            return;
        }

        gz::sim::Model projectileModel(
            this->projectileModelEntity);

        if (!projectileModel.Valid(_ecm))
        {
            return;
        }

        if (!this->initialized)
        {
            if (!this->initializeProjectile(
                    _info,
                    _ecm,
                    projectileModel))
            {
                return;
            }

            return;
        }

        const double flightTime =
            std::chrono::duration<double>(
                _info.simTime - this->startTime
            ).count();

        gz::math::Vector3d position =
            this->initialPosition
            + this->worldVelocity * flightTime;

        position.Z(
            position.Z()
            - 0.5
            * this->gravity
            * flightTime
            * flightTime);

        if (
            position.Z() <= this->groundZ
            || flightTime >= this->maxFlightTime)
        {
            position.Z(this->groundZ);

            projectileModel.SetWorldPoseCmd(
                _ecm,
                gz::math::Pose3d(
                    position,
                    this->initialRotation));

            this->finished = true;

            gzmsg
                << "[ProjectileLaunchSystem] "
                << "Mermi uçuşu tamamlandı | "
                << "süre="
                << flightTime
                << " s | son konum="
                << position
                << std::endl;

            return;
        }

        projectileModel.SetWorldPoseCmd(
            _ecm,
            gz::math::Pose3d(
                position,
                this->initialRotation));
    }

private:
    bool initializeProjectile(
        const gz::sim::UpdateInfo &_info,
        gz::sim::EntityComponentManager &_ecm,
        gz::sim::Model &_projectileModel)
    {
        const std::string scopedName =
            this->referenceModel
            + "::"
            + this->referenceLink;

        const auto entities =
            gz::sim::entitiesFromScopedName(
                scopedName,
                _ecm);

        gz::sim::Entity muzzleEntity =
            gz::sim::kNullEntity;

        for (const auto entity : entities)
        {
            gz::sim::Link candidate(entity);

            if (candidate.Valid(_ecm))
            {
                muzzleEntity = entity;
                break;
            }
        }

        if (muzzleEntity == gz::sim::kNullEntity)
        {
            return false;
        }

        const gz::math::Pose3d muzzlePose =
            gz::sim::worldPose(
                muzzleEntity,
                _ecm);

        const gz::math::Vector3d forwardOffset =
            muzzlePose.Rot().RotateVector(
                gz::math::Vector3d(
                    this->clearance,
                    0.0,
                    0.0));

        this->initialPosition =
            muzzlePose.Pos() + forwardOffset;

        this->initialRotation =
            muzzlePose.Rot();

        this->worldVelocity =
            muzzlePose.Rot().RotateVector(
                this->localVelocity);

        this->startTime = _info.simTime;
        this->initialized = true;

        _projectileModel.SetWorldPoseCmd(
            _ecm,
            gz::math::Pose3d(
                this->initialPosition,
                this->initialRotation));

        gzmsg
            << "[ProjectileLaunchSystem] "
            << "Mermi namludan ateşlendi | "
            << "başlangıç="
            << this->initialPosition
            << " | dünya hızı="
            << this->worldVelocity
            << " m/s"
            << std::endl;

        return true;
    }

private:
    gz::sim::Entity projectileModelEntity{
        gz::sim::kNullEntity};

    std::string referenceModel{
        "heybeliada_ship"};

    std::string referenceLink{
        "muzzle_link"};

    gz::math::Vector3d localVelocity{
        18.0,
        0.0,
        0.0};

    gz::math::Vector3d worldVelocity{
        18.0,
        0.0,
        0.0};

    gz::math::Vector3d initialPosition{
        0.0,
        0.0,
        0.0};

    gz::math::Quaterniond initialRotation{
        1.0,
        0.0,
        0.0,
        0.0};

    std::chrono::steady_clock::duration startTime{
        std::chrono::steady_clock::duration::zero()};

    double clearance{0.55};
    double gravity{9.81};
    double groundZ{0.12};
    double maxFlightTime{20.0};

    bool initialized{false};
    bool finished{false};
};

}  // namespace projectile_launch_plugin


GZ_ADD_PLUGIN(
    projectile_launch_plugin::ProjectileLaunchSystem,
    gz::sim::System,
    projectile_launch_plugin::ProjectileLaunchSystem::ISystemConfigure,
    projectile_launch_plugin::ProjectileLaunchSystem::ISystemPreUpdate)

GZ_ADD_PLUGIN_ALIAS(
    projectile_launch_plugin::ProjectileLaunchSystem,
    "projectile_launch_plugin::ProjectileLaunchSystem")
