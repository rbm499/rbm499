package com.aaadnw.commscap.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class LookbackPlannerTest {
    private val h = LookbackPlanner.HOUR_MS
    private val now = 1_790_000_000_000L
    private val a = "+12065550177"
    private val b = "+12065550150"

    private fun ref(uid: String, addr: String, ageHours: Double) =
        DeferredRef(uid, addr, now - (ageHours * h).toLong())

    @Test
    fun promotesSameAddressOldestFirst() {
        val plan = LookbackPlanner.plan(
            listOf(ref("new", a, 1.0), ref("old", a, 10.0), ref("mid", a, 5.0), ref("other", b, 2.0)),
            a, now, 24,
        )
        assertEquals(listOf("old", "mid", "new"), plan.promoteUids)
        assertEquals(emptyList<String>(), plan.expireUids)
    }

    @Test
    fun ageBoundaryIsExclusiveForPromotionAndInclusiveForExpiry() {
        val plan = LookbackPlanner.plan(listOf(ref("exact", a, 24.0), ref("justUnder", a, 23.99)), a, now, 24)
        assertEquals(listOf("justUnder"), plan.promoteUids)
        assertEquals(listOf("exact"), plan.expireUids)
    }

    @Test
    fun expiredOnesAreReportedForEveryAddress() {
        val plan = LookbackPlanner.plan(listOf(ref("x", b, 30.0), ref("y", a, 25.0), ref("z", b, 1.0)), a, now, 24)
        assertEquals(emptyList<String>(), plan.promoteUids)
        assertEquals(listOf("x", "y"), plan.expireUids)
    }

    @Test
    fun addressesAreCompared_canonically() {
        val plan = LookbackPlanner.plan(listOf(ref("u", "(206) 555-0177", 1.0)), "206-555-0177", now, 24)
        assertEquals(listOf("u"), plan.promoteUids)
    }

    @Test
    fun nonPhoneAddressesMatchOnTrimmedText() {
        val plan = LookbackPlanner.plan(listOf(ref("u", "CHASE", 1.0)), " CHASE ", now, 24)
        assertEquals(listOf("u"), plan.promoteUids)
    }

    @Test
    fun blankSendAddressPromotesNothing() {
        assertEquals(emptyList<String>(), LookbackPlanner.plan(listOf(ref("u", a, 1.0)), "  ", now, 24).promoteUids)
    }

    @Test
    fun zeroDeferHoursExpiresEverything() {
        val plan = LookbackPlanner.plan(listOf(ref("u", a, 0.0)), a, now, 0)
        assertEquals(emptyList<String>(), plan.promoteUids)
        assertEquals(listOf("u"), plan.expireUids)
    }

    @Test
    fun equalTimestampsTieBreakOnUid() {
        val t = now - h
        val plan = LookbackPlanner.plan(listOf(DeferredRef("b", a, t), DeferredRef("a", a, t)), a, now, 24)
        assertEquals(listOf("a", "b"), plan.promoteUids)
    }

    @Test
    fun heldMessagesExpireByDays() {
        val held = listOf(ref("old", a, 8 * 24.0), ref("fresh", a, 6 * 24.0))
        assertEquals(listOf("old"), LookbackPlanner.expired(held, now, 7 * LookbackPlanner.DAY_MS))
    }
}
