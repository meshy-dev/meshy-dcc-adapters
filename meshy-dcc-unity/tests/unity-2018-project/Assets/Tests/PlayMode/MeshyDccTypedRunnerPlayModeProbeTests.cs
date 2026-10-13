using System.Collections;
using NUnit.Framework;
using UnityEngine.TestTools;

namespace MeshyDcc.Unity.LiveTests
{
    public sealed class MeshyDccTypedRunnerPlayModeProbeTests
    {
        [UnityTest]
        public IEnumerator ExactFilteredProjectTestSurvivesPlayModeTransition()
        {
            yield return null;
            Assert.That(true, Is.True);
        }
    }
}
