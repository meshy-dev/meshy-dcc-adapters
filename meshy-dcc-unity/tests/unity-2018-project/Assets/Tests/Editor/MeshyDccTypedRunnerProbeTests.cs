using NUnit.Framework;

namespace MeshyDcc.Unity.LiveTests
{
    public sealed class MeshyDccTypedRunnerProbeTests
    {
        [Test]
        public void ExactFilteredProjectTestRunsInsideTheConnectedEditor()
        {
            Assert.That(1 + 1, Is.EqualTo(2));
        }
    }
}
